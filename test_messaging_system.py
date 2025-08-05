#!/usr/bin/env python3
"""
Test script for Fetch Bites messaging system
Validates all user-facing copy and personalization features
"""

import os
import sys
from typing import List, Dict

# Add src to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.utils.fetch_bites_messages import FetchBitesMessages, get_message, get_onboarding_messages, get_error_message

class MessageTester:
    def __init__(self):
        self.messages = FetchBitesMessages()
        self.test_users = [
            "docteurzed",
            "thesoush", 
            "chef_marco",
            "audio-call",
            "unknown",
            "",
            None,
            "very.long.username.with.lots.of.dots",
            "user_with_underscores",
            "@instagram_handle"
        ]
        self.test_results = []
    
    def test_name_cleaning(self):
        """Test user name cleaning and personalization"""
        print("🧪 Testing Name Cleaning & Personalization")
        print("=" * 50)
        
        for user in self.test_users:
            clean_name = self.messages._clean_user_name(user)
            print(f"Original: '{user}' → Cleaned: '{clean_name}'")
        print()
    
    def test_onboarding_flow(self):
        """Test onboarding message sequence"""
        print("🚀 Testing Onboarding Flow")
        print("=" * 50)
        
        for user in ["docteurzed", "thesoush", None]:
            print(f"\n📱 Onboarding for user: {user}")
            print("-" * 30)
            messages = get_onboarding_messages(user)
            for i, msg in enumerate(messages, 1):
                print(f"Message {i}: {msg}")
                print()
    
    def test_recipe_processing_messages(self):
        """Test recipe processing flow messages"""
        print("🍽️ Testing Recipe Processing Messages")
        print("=" * 50)
        
        test_scenarios = [
            ("recipe_processing_start", "docteurzed"),
            ("recipe_extraction_success", "thesoush"),
            ("recipe_ready_no_email", "chef_marco"),
            ("pdf_sent_success", "docteurzed")
        ]
        
        for message_type, user in test_scenarios:
            msg = get_message(message_type, user)
            print(f"\n📝 {message_type} for {user}:")
            print(f"   {msg}")
    
    def test_error_handling_messages(self):
        """Test error message variations"""
        print("❌ Testing Error Handling Messages")
        print("=" * 50)
        
        error_scenarios = [
            ("extraction_failed", "docteurzed"),
            ("language_issue", "thesoush"),
            ("processing_error", "chef_marco"),
            ("no_recipe_found", "unknown")
        ]
        
        for error_type, user in error_scenarios:
            msg = get_error_message(error_type, user)
            print(f"\n🚨 {error_type} for {user}:")
            print(f"   {msg}")
    
    def test_email_flow_messages(self):
        """Test email-related messaging"""
        print("📧 Testing Email Flow Messages")
        print("=" * 50)
        
        email_scenarios = [
            ("email_request", "docteurzed"),
            ("email_confirmation", "thesoush"), 
            ("email_not_received", "chef_marco")
        ]
        
        for message_type, user in email_scenarios:
            msg = get_message(message_type, user)
            print(f"\n✉️ {message_type} for {user}:")
            print(f"   {msg}")
    
    def test_engagement_messages(self):
        """Test user engagement and feedback messages"""
        print("💬 Testing User Engagement Messages")
        print("=" * 50)
        
        engagement_scenarios = [
            ("returning_user_greeting", "docteurzed"),
            ("feedback_request", "thesoush"),
            ("generic_help", "chef_marco")
        ]
        
        for message_type, user in engagement_scenarios:
            msg = get_message(message_type, user)
            print(f"\n🤝 {message_type} for {user}:")
            print(f"   {msg}")
    
    def test_message_consistency(self):
        """Validate message consistency and formatting"""
        print("✅ Testing Message Consistency")
        print("=" * 50)
        
        issues = []
        
        # Check all messages exist
        required_messages = [
            "onboarding_welcome", "onboarding_instructions", "onboarding_value_prop",
            "recipe_processing_start", "recipe_extraction_success", "recipe_ready_no_email",
            "recipe_extraction_failed", "language_extraction_issue",
            "email_request", "email_confirmation", "email_not_received",
            "pdf_sent_success", "processing_error", "generic_help"
        ]
        
        for msg_type in required_messages:
            try:
                msg = get_message(msg_type, "test_user")
                if not msg or len(msg.strip()) < 10:
                    issues.append(f"Message '{msg_type}' is too short or empty")
            except Exception as e:
                issues.append(f"Error retrieving message '{msg_type}': {e}")
        
        # Check personalization works
        personal_msg = get_message("onboarding_welcome", "docteurzed")
        generic_msg = get_message("onboarding_welcome", None)
        
        if "Docteurzed" not in personal_msg:
            issues.append("Personalization not working for onboarding_welcome")
        
        if "there" not in generic_msg:
            issues.append("Fallback personalization not working")
        
        if issues:
            print("❌ Issues found:")
            for issue in issues:
                print(f"   • {issue}")
        else:
            print("✅ All consistency checks passed!")
        
        print()
    
    def test_message_lengths(self):
        """Check message lengths for Instagram DM limits"""
        print("📏 Testing Message Lengths")
        print("=" * 50)
        
        long_messages = []
        
        for msg_type in self.messages.messages.keys():
            msg = get_message(msg_type, "test_user")
            length = len(msg)
            if length > 1000:  # Instagram DM limit is around 1000 chars
                long_messages.append((msg_type, length))
        
        if long_messages:
            print("⚠️ Messages that might be too long for Instagram DMs:")
            for msg_type, length in long_messages:
                print(f"   • {msg_type}: {length} characters")
        else:
            print("✅ All messages are within reasonable length limits!")
        
        print()
    
    def run_all_tests(self):
        """Run the complete test suite"""
        print("🎯 FETCH BITES MESSAGING SYSTEM TEST")
        print("=" * 60)
        print()
        
        self.test_name_cleaning()
        self.test_onboarding_flow()
        self.test_recipe_processing_messages()
        self.test_error_handling_messages()
        self.test_email_flow_messages()
        self.test_engagement_messages()
        self.test_message_consistency()
        self.test_message_lengths()
        
        print("🏁 Testing Complete!")
        print("=" * 60)
        print("\n💡 To test with the live agent:")
        print("   1. Start the agent: python appium_actor.py")
        print("   2. Send test messages from different Instagram accounts")
        print("   3. Verify personalization and message flow")
        print("   4. Test error scenarios (non-recipe posts)")
        print("   5. Test email collection and PDF delivery")

def main():
    """Main test execution"""
    tester = MessageTester()
    tester.run_all_tests()

if __name__ == "__main__":
    main()