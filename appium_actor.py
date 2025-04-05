import os
from time import sleep
from appium import webdriver
from dotenv import load_dotenv
from appium.options.ios import XCUITestOptions

# Load all environment variables from the .env file
load_dotenv()

# Instagram credentials and other variables
INSTAGRAM_USERNAME = os.getenv("INSTAGRAM_USERNAME")
INSTAGRAM_PASSWORD = os.getenv("INSTAGRAM_PASSWORD")
# ... (other env variables)

print("Loaded .env configuration:")
print("Instagram Username:", INSTAGRAM_USERNAME)

# Create an options object for iOS
options = XCUITestOptions()
options.device_name = "iPhone"         # Update as needed
options.platform_version = "18.3"       # Update to match your device's iOS version
options.udid = "00008101-000A4D320A28001E"  # Your device's UDID
options.bundle_id = "com.burbn.instagram"  # Correct bundle identifier for Instagram
options.xcode_org_id = "6X85PLZ26L"      # Your Apple Developer team ID
options.xcode_signing_id = "Apple Developer"  # Typically "iPhone Developer"
options.set_capability("showXcodeLog", True)    # Enable detailed Xcode logs
options.set_capability("usePrebuiltWDA", True)
# options.set_capability("useNewWDA", True)

# Connect to the Appium server using the options object
driver = webdriver.Remote("http://127.0.0.1:4723", options=options)

try:
    # Wait for the app to load
    sleep(10)
    
    # Step 1: Tap the DM (threads/conversations) button using an XPath from Appium Inspector
    dm_button = driver.find_element("-ios predicate string", "name == 'direct-inbox'")
    dm_button.click()
    print("Tapped DM button using XPath.")
    sleep(3)

    while True:
        # Step 2: Scan for unread conversations by looking for 'Unseen'
        unread_threads = driver.find_elements(
            "xpath",
            "//XCUIElementTypeCell[.//*[@name='Unseen']]"
        )
        print(f"Found {len(unread_threads)} unread thread(s).")

        if len(unread_threads) == 0:
            print("No unread messages found. Sleeping for 60 seconds...")
            sleep(60)
            continue  # Go back to the start of the loop

        # Step 3: Follow onboarding flow for each unread thread
        for thread in unread_threads:
            thread.click()
            sleep(2)

            try:
                # Step 1: Tap on the avatar button
                avatar_button = driver.find_element(
                    "-ios class chain",
                    "**/XCUIElementTypeButton[`name == \"avatar-front-image-view\"`]"
                )
                avatar_button.click()
                sleep(2)

                # Step 2: Find the navigation bar button that is not the back button
                user_id = None
                nav_buttons = driver.find_elements(
                    "-ios class chain",
                    "**/XCUIElementTypeNavigationBar/XCUIElementTypeButton"
                )
                for btn in nav_buttons:
                    btn_name = btn.get_attribute("name")
                    if btn_name != "profile-back-button":
                        user_id = btn_name
                        break

                if not user_id:
                    print("[WARNING] Could not identify user ID from navigation bar.")
                    user_id = "<unknown_user>"

                # Step 3: Tap on the back button to return to the thread
                back_button = driver.find_element(
                    "-ios class chain",
                    "**/XCUIElementTypeButton[`name == \"profile-back-button\"`]"
                )
                back_button.click()
                sleep(2)

                # Step 4: Onboarding logic
                is_onboarded = False  # Replace with actual check from your onboarding manager
                if not is_onboarded:
                    print(f"Onboarding user {user_id}...")

                    onboarding_messages = [
                        "Hey! I’m your recipe assistant. If you send me a shared recipe post, I’ll extract the full recipe and send you back a clean PDF copy.",
                        "Just paste or forward any Instagram recipe post. I’ll do the rest — no sign-up needed.",
                        "Want your recipes saved or emailed to you? Just say \"email me\" and I’ll set that up."
                    ]

                    # Send each message in turn
                    for msg in onboarding_messages:
                        # Locate text input
                        text_input = driver.find_element(
                            "-ios predicate string", 
                            "type == 'XCUIElementTypeTextView' AND visible == 1"
                        )
                        text_input.send_keys(msg)
                        sleep(1)

                        # Tap the send button
                        send_button = driver.find_element(
                            "-ios class chain",
                            "**/XCUIElementTypeButton[`name == \"send button\"`]"
                        )
                        send_button.click()
                        sleep(2)

                    # Here, integrate your onboarding manager to mark the user as onboarded (e.g., update a memory file or DB)
                    print(f"User {user_id} has been onboarded.")
                else:
                    print(f"User {user_id} is already onboarded.")
            except Exception as e:
                print(f"[ERROR] Failed to retrieve user info or onboard: {e}")

            # Sleep briefly between processing threads
            sleep(2)

        # After processing all unread threads, ask the user if they want to quit
        print("Completed processing current unread threads. Scanning again...")
        exit_choice = input("Press 'q' to quit scanning, or press Enter to continue: ")
        if exit_choice.lower() == 'q':
            print("Exiting continuous scanning loop.")
            break

        sleep(2)

except Exception as e:
    print(f"An error occurred during login automation: {e}")

finally:
    driver.quit()