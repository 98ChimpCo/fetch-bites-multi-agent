# src/agents/pdf_generator.py
import os
import pathlib
import logging
import time
import json
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from io import BytesIO
from PIL import Image
from reportlab.lib.pagesizes import LETTER, A4, LEGAL, TABLOID
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, Image as RLImage, TableStyle, Frame, PageTemplate, Flowable, KeepInFrame
from reportlab.graphics.shapes import Drawing, Circle, String
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from urllib.parse import urlparse, urlunparse
from src.agents.pdf_cache import PDFCache

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)


class NumberedCircle(Flowable):
    """Custom flowable for creating numbered circles"""

    def __init__(self, number, text, width=400, height=18, *, circle_radius=8, num_offset_y=-4, text_size=11, line_height=13):
        Flowable.__init__(self)
        self.number = number
        self.text = text
        self.width = width
        self.height = height
        self.circle_radius = circle_radius
        self.num_offset_y = num_offset_y
        self.text_size = text_size
        self.line_height = line_height

    def draw(self):
        # Font selection for badge and text
        try:
            _badge_font = 'Poppins-Bold'
            pdfmetrics.getFont(_badge_font)
        except Exception:
            _badge_font = 'Helvetica-Bold'
        # Draw a slightly smaller circle and tighter text layout
        from reportlab.pdfgen import canvas
        # Circle geometry
        circle_radius = self.circle_radius
        circle_x = circle_radius + 2
        circle_y = self.height / 2

        # Black circle with white number
        self.canv.setFillColor(colors.black)
        self.canv.circle(circle_x, circle_y, circle_radius, fill=1)

        # White number text, better vertical centering
        self.canv.setFillColor(colors.white)
        self.canv.setFont(_badge_font, 10)
        text_width = self.canv.stringWidth(str(self.number), _badge_font, 10)
        text_x = circle_x - (text_width / 2)
        # Tighter vertical centering in circle
        text_y = circle_y - 4
        self.canv.drawString(text_x, text_y, str(self.number))

        # Draw instruction text, line height from layout
        self.canv.setFillColor(colors.black)
        self.canv.setFont('Poppins-Regular' if _badge_font.startswith('Poppins') else 'Helvetica', self.text_size)
        text_start_x = circle_x + circle_radius + 8
        text_start_y = circle_y + self.num_offset_y + 1
        from reportlab.pdfbase.pdfmetrics import stringWidth
        available_width = self.width - text_start_x - 10
        words = self.text.split(' ')
        lines = []
        current_line = []
        for word in words:
            test_line = ' '.join(current_line + [word])
            if stringWidth(test_line, 'Poppins-Regular' if _badge_font.startswith('Poppins') else 'Helvetica', self.text_size) <= available_width:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(' '.join(current_line))
                    current_line = [word]
                else:
                    lines.append(word)
        if current_line:
            lines.append(' '.join(current_line))
        # Draw each line, layout-driven line height
        for i, line in enumerate(lines):
            line_y = text_start_y - (i * self.line_height)
            self.canv.drawString(text_start_x, line_y, line)
        # Adjust height for multi-line
        if len(lines) > 1:
            self.height = max(18, len(lines) * self.line_height + 4)


# --- RoundedTable Flowable for notes background ---
class RoundedTable(Flowable):
    """A wrapper that draws a rounded rectangle behind a Table/Flowable."""
    def __init__(self, inner_table, width, padding=16, radius=10, bg=colors.HexColor('#F8F8F8'), stroke=colors.HexColor('#E0E0E0'), stroke_width=1):
        super().__init__()
        self.inner = inner_table
        self.width = width
        self.padding = padding
        self.radius = radius
        self.bg = bg
        self.stroke = stroke
        self.stroke_width = stroke_width
        self._wrapped = False
        self._inner_w = 0
        self._inner_h = 0

    def wrap(self, availWidth, availHeight):
        # Constrain to provided width
        iw, ih = self.inner.wrap(self.width - 2*self.padding, availHeight)
        self._inner_w, self._inner_h = iw, ih
        total_w = self.width
        total_h = ih + 2*self.padding
        self._wrapped = True
        return total_w, total_h

    def draw(self):
        if not self._wrapped:
            # Fallback sizing if wrap was not called
            self._inner_w, self._inner_h = self.inner.wrap(self.width - 2*self.padding, 10000)
        w = self.width
        h = self._inner_h + 2*self.padding
        r = self.radius
        c = self.canv
        c.saveState()
        # Background rounded rect
        c.setFillColor(self.bg)
        c.setStrokeColor(self.stroke)
        c.setLineWidth(self.stroke_width)
        c.roundRect(0, 0, w, h, r, stroke=1, fill=1)
        # Draw inner at padding offset
        self.inner.drawOn(c, self.padding, self.padding)
        c.restoreState()

# --- FooterBand Flowable for full-width footer band with centered child, natural height ---
class FooterBand(Flowable):
    """Full-width light-grey band that wraps a child (e.g., RoundedTable) with padding and centers it.
    Natural height = child's wrapped height + vertical padding. This lets us anchor the band to the
    bottom via a spacer in _generate_pdf_v2 without forcing a fixed band height.
    """
    def __init__(self, child: Flowable, width: float, *, band_bg=colors.HexColor('#F3F4F6'),
                 band_pad_h=20, band_pad_v=14, child_width=None):
        super().__init__()
        self.child = child
        self.width = width
        self.band_bg = band_bg
        self.band_pad_h = band_pad_h
        self.band_pad_v = band_pad_v
        self.child_width = child_width or (width - 2*band_pad_h)
        self._child_w = 0
        self._child_h = 0

    def wrap(self, availWidth, availHeight):
        cw, ch = self.child.wrap(self.child_width, max(0, availHeight - 2*self.band_pad_v))
        self._child_w, self._child_h = cw, ch
        total_w = self.width
        total_h = self.band_pad_v*2 + ch
        return total_w, total_h

    def draw(self):
        c = self.canv
        c.saveState()
        bw, bh = self.width, self.band_pad_v*2 + self._child_h
        # Draw band background across full width with natural height
        c.setFillColor(self.band_bg)
        c.setStrokeColor(self.band_bg)
        c.rect(0, 0, bw, bh, stroke=0, fill=1)
        # Center child horizontally and vertically within the band
        x = (bw - self._child_w) / 2.0
        y = (bh - self._child_h) / 2.0
        self.child.drawOn(c, x, y)
        c.restoreState()

class BottomAnchor(Flowable):
    """Consumes remaining height so the next flowable (footer band) sits at the bottom of the page."""
    def __init__(self, footer: Flowable, width: float):
        super().__init__()
        self.footer = footer
        self.width = width
        self._footer_h = 0

    def wrap(self, availWidth, availHeight):
        try:
            _, fh = self.footer.wrap(self.width, availHeight)
        except Exception:
            fh = 0
        self._footer_h = max(0, fh)
        # occupy all remaining height except what the footer needs
        h = max(0, availHeight - self._footer_h)
        return self.width, h

    def draw(self):
        pass  # just takes up space

class PDFGenerator:
    def _resolve_icon_path(self, icon_filename: str) -> Optional[str]:
        """Try multiple filename variants and extensions under assets/icons."""
        from pathlib import Path
        base = Path(icon_filename).stem.replace(' ', '_')
        candidates = []
        # try original
        candidates.append(self.icons_dir / icon_filename)
        # dash/underscore variants
        variants = {base, base.replace('-', '_'), base.replace('_', '-')}
        exts = ['.png', '.webp', '.jpg', '.jpeg']
        for v in variants:
            for ext in exts:
                candidates.append(self.icons_dir / f"{v}{ext}")
        for cand in candidates:
            p = str(cand)
            if os.path.exists(p):
                return p
        logger.debug("Icon not found for %s; tried: %s", icon_filename, ", ".join(str(c) for c in candidates))
        return None
    
    def _icon_exists(self, icon_filename: str) -> bool:
        path = self._resolve_icon_path(icon_filename)
        return bool(path)

    def _icon_text_cell(self, icon_filename: str, text: str, *, style_name: str = 'StatsInline', icon_px: int = 12):
        """Return a small [icon + text] cell (Table) if icon exists, else a Paragraph(text).
        Looks for icons under assets/icons/; default style is 'StatsInline'. Use style_name='ChefInfo' for header rows.
        """
        try:
            from reportlab.platypus import Table, TableStyle, Paragraph, Image as RLImage
            path = self._resolve_icon_path(icon_filename)
            if path:
                img = RLImage(path, width=icon_px, height=icon_px)
                t = Table([[img, Paragraph(text, self.styles[style_name])]], colWidths=[icon_px + 2, None])
                logger.debug(f"Loaded icon: {icon_filename} -> {path}")
                t.setStyle(TableStyle([
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('LEFTPADDING', (0, 0), (-1, -1), 0),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 0),
                    ('TOPPADDING', (0, 0), (-1, -1), 0),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
                ]))
                return t
        except Exception as e:
            logger.warning(f"_icon_text_cell fallback to text for {icon_filename} at {path if path else '<not-found>'}: {e}")
        # Fallback: text only
        return Paragraph(text, self.styles.get(style_name, self.styles['StatsInline']))
    
    def __init__(self, output_dir='pdfs'):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        self.accent_color = colors.HexColor('#FF8C42')  # Orange color from template
        self.text_color = colors.HexColor('#333333')
        self.gray_color = colors.HexColor('#666666')
        self.light_gray = colors.HexColor('#F5F5F5')
        self.notes_bg = colors.HexColor('#F8F8F8')  # Light gray for notes background
        self.page_width = LETTER[0]
        self.styles = getSampleStyleSheet()

        # Resolve absolute asset directories (override with ASSETS_DIR if provided)
        start = pathlib.Path(__file__).resolve()
        env_assets = os.getenv('ASSETS_DIR')
        assets_dir = None
        if env_assets and os.path.isdir(env_assets):
            assets_dir = pathlib.Path(env_assets)
        else:
            # Walk up until we find an `assets` directory
            for parent in [start] + list(start.parents):
                candidate = parent / 'assets'
                if candidate.exists() and candidate.is_dir():
                    assets_dir = candidate
                    break
            # Fallback: try CWD/assets
            if assets_dir is None:
                cwd_candidate = pathlib.Path(os.getcwd()) / 'assets'
                if cwd_candidate.exists() and cwd_candidate.is_dir():
                    assets_dir = cwd_candidate
        # Final fallback: create a local assets dir to avoid None paths
        if assets_dir is None:
            assets_dir = start.parent / 'assets'
        self.assets_dir = assets_dir
        self.icons_dir = self.assets_dir / 'icons'
        self.fonts_dir = self.assets_dir / 'fonts'

        # --- Font registration: SF Pro (.otf) if available ---
        def _register_sf_font(alias, filenames):
            for fn in filenames:
                path = os.path.join(str(self.fonts_dir), fn)
                if os.path.exists(path):
                    try:
                        pdfmetrics.registerFont(TTFont(alias, path))
                        logger.info(f"Registered font {alias} from {path}")
                        return True
                    except Exception as e:
                        logger.warning(f"Failed to register {alias} from {path}: {e}")
            return False

        has_light   = _register_sf_font('SFPro-Light',    ['SFProText-Light.otf', 'SFProText-LightItalic.otf', 'SF-Pro-Text-Light.otf'])
        has_regular = _register_sf_font('SFPro-Regular',  ['SFProText-Regular.otf', 'SF-Pro-Text-Regular.otf'])
        has_semibold= _register_sf_font('SFPro-Semibold', ['SFProText-Semibold.otf', 'SF-Pro-Text-Semibold.otf'])
        has_bold    = _register_sf_font('SFPro-Bold',     ['SFProText-Bold.otf', 'SF-Pro-Text-Bold.otf'])

        if has_regular and has_bold:
            try:
                pdfmetrics.registerFontFamily('SFPro', normal='SFPro-Regular', bold='SFPro-Bold', italic='SFPro-Regular', boldItalic='SFPro-Bold')
            except Exception as e:
                logger.warning(f"Could not register font family SFPro: {e}")

        # --- Poppins font registration (preferred) ---
        def _register_ttf(alias, filenames):
            for fn in filenames:
                path = os.path.join(str(self.fonts_dir), fn)
                if os.path.exists(path):
                    try:
                        pdfmetrics.registerFont(TTFont(alias, path))
                        logger.info(f"Registered font {alias} from {path}")
                        return True
                    except Exception as e:
                        logger.warning(f"Failed to register {alias} from {path}: {e}")
            return False

        has_pop_light    = _register_ttf('Poppins-Light',   ['Poppins-Light.ttf'])
        has_pop_regular  = _register_ttf('Poppins-Regular', ['Poppins-Regular.ttf'])
        has_pop_semibold = _register_ttf('Poppins-SemiBold',['Poppins-SemiBold.ttf'])
        has_pop_bold     = _register_ttf('Poppins-Bold',    ['Poppins-Bold.ttf'])
        has_pop_italic   = _register_ttf('Poppins-Italic',  ['Poppins-Italic.ttf'])

        if has_pop_regular or has_pop_bold:
            try:
                pdfmetrics.registerFontFamily(
                    'Poppins',
                    normal='Poppins-Regular' if has_pop_regular else ('Poppins-Light' if has_pop_light else 'Helvetica'),
                    bold='Poppins-Bold' if has_pop_bold else ('Poppins-SemiBold' if has_pop_semibold else 'Helvetica-Bold'),
                    italic='Poppins-Italic' if has_pop_italic else ('Poppins-Regular' if has_pop_regular else 'Helvetica-Oblique'),
                    boldItalic='Poppins-Bold' if has_pop_bold else ('Poppins-SemiBold' if has_pop_semibold else 'Helvetica-Bold')
                )
            except Exception as e:
                logger.warning(f"Could not register font family Poppins: {e}")

        # Load external layout config if provided
        self.layout = self._load_layout()

        def _lv(keys, default):
            node = self.layout or {}
            for k in keys:
                if isinstance(node, dict) and k in node:
                    node = node[k]
                else:
                    return default
            return node
        self._lv = _lv
        logger.info(f"Layout config path: {os.getenv('LAYOUT_CONFIG', 'layout.v2.json')} | keys: {list(self.layout.keys()) if isinstance(self.layout, dict) else 'none'}")

        # Preferred font family: Poppins -> SF Pro -> Helvetica
        if has_pop_regular or has_pop_bold or has_pop_light or has_pop_semibold:
            base_title_font   = 'Poppins-Bold' if has_pop_bold or has_pop_semibold else 'Poppins-Regular'
            base_heading_font = 'Poppins-SemiBold' if has_pop_semibold else ('Poppins-Bold' if has_pop_bold else 'Poppins-Regular')
            base_body_font    = 'Poppins-Light' if has_pop_light else ('Poppins-Regular' if has_pop_regular else base_title_font)
            base_meta_font    = 'Poppins-Regular' if has_pop_regular else (base_body_font)
        else:
            base_title_font   = 'SFPro-Bold' if has_bold else 'Helvetica-Bold'
            base_heading_font = 'SFPro-Semibold' if has_semibold else ('SFPro-Bold' if has_bold else 'Helvetica-Bold')
            base_body_font    = 'SFPro-Light' if has_light else ('SFPro-Regular' if has_regular else 'Helvetica')
            base_meta_font    = 'SFPro-Regular' if has_regular else 'Helvetica'

        # Expose a bold font name for badge glyphs
        self.badge_bold_font = (
            'Poppins-Bold' if (has_pop_bold or has_pop_semibold or has_pop_regular) else
            ('SFPro-Bold' if has_bold else 'Helvetica-Bold')
        )

        # Choose italic face for Notes body when available
        notes_font = 'Poppins-Italic' if has_pop_italic else (
            'Poppins-Regular' if has_pop_regular else 'Helvetica-Oblique'
        )
        # Typography styles
        self.styles.add(ParagraphStyle(name='RecipeTitle', fontName=base_meta_font, fontSize=22, leading=24, alignment=0, textColor=self.text_color, spaceAfter=12))
        self.styles.add(ParagraphStyle(name='RecipeDescription', fontName=base_body_font, fontSize=10.5, leading=14, alignment=0, textColor=colors.HexColor('#555555'), spaceAfter=0))
        self.styles.add(ParagraphStyle(name='ChefInfo', fontName=base_meta_font, fontSize=9, leading=12, alignment=0, textColor=self.gray_color, spaceAfter=0))
        self.styles.add(ParagraphStyle(name='SectionTitle', fontName=base_heading_font, fontSize=15, leading=17, textColor=self.text_color, spaceAfter=8))
        self.styles.add(ParagraphStyle(name='SectionTitleCentered', fontName=base_heading_font, fontSize=15, leading=17, textColor=self.text_color, alignment=1, spaceAfter=8))
        self.styles.add(ParagraphStyle(name='NotesTitle', fontName=base_meta_font, fontSize=15, leading=17, textColor=self.text_color, spaceAfter=8))
        self.styles.add(ParagraphStyle(name='IngredientItem', fontName=base_body_font, fontSize=10.5, leading=15, leftIndent=0, spaceAfter=6))
        self.styles.add(ParagraphStyle(name='InstructionItem', fontName=base_body_font, fontSize=10.5, leading=16, leftIndent=0, spaceAfter=8))
        self.styles.add(ParagraphStyle(name='InstructionNumber', fontName=base_body_font, fontSize=10.5, leading=15, spaceAfter=4))
        self.styles.add(ParagraphStyle(name='StatsInline', fontName=base_meta_font, fontSize=7.5, leading=10, textColor=self.gray_color, alignment=0, spaceAfter=0))
        self.styles.add(ParagraphStyle(name='StatsLabel', fontName=base_meta_font, fontSize=9, leading=12, textColor=self.gray_color, alignment=1))
        self.styles.add(ParagraphStyle(name='StatsValue', fontName=base_heading_font, fontSize=12.5, leading=14, textColor=self.text_color, alignment=1))
        self.styles.add(ParagraphStyle(name='Notes', fontName=notes_font, fontSize=10.5, leading=15, textColor=self.gray_color))
        self.styles.add(ParagraphStyle(name='Footer', fontName=base_meta_font, fontSize=8.5, leading=10, textColor=colors.gray, alignment=1))

        # Cache & URL settings
        self.cache = PDFCache()
        self.enable_url_shortening = os.getenv('URL_SHORTENING', 'false').lower() in ('1','true','yes','on')
        self.shorten_domains = [d.strip().lower() for d in os.getenv('SHORTEN_ONLY_DOMAINS', 'instagram.com').split(',') if d.strip()]

    def _get_pagesize(self):
        """Pick page size from env or recipe data; defaults to LETTER. Supports: LETTER, A4, LEGAL, TABLOID."""
        name = os.getenv('PAGE_SIZE', '').strip().upper()
        if name == 'A4':
            return A4
        if name == 'LEGAL':
            return LEGAL
        if name == 'TABLOID':
            return TABLOID
        # default
        return LETTER

    def _load_layout(self):
        path = os.getenv('LAYOUT_CONFIG', 'layout.v2.json')
        try:
            if os.path.exists(path):
                with open(path, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.info(f"Layout config not loaded ({path}): {e}")
        return {}

    def _clean_url(self, url: str) -> str:
        try:
            if not url:
                return ''
            p = urlparse(url)
            p = p._replace(query='', fragment='')
            return urlunparse(p)
        except Exception:
            return url.split('?')[0]

    def _shorten_url(self, url: str) -> Optional[str]:
        if not url or not self.enable_url_shortening:
            return None
        # Only shorten for allowed domains
        try:
            from urllib.parse import urlparse
            dom = urlparse(url).netloc.lower().split(':')[0]
            if not any(dom == d or dom.endswith('.' + d) for d in getattr(self, 'shorten_domains', ['instagram.com'])):
                return None
        except Exception:
            return None
        try:
            import requests
            resp = requests.get('https://tinyurl.com/api-create.php', params={'url': url}, timeout=4)
            if resp.status_code == 200:
                s = resp.text.strip()
                if s.startswith('http') and len(s) < len(url):
                    return s
        except Exception as e:
            logger.info(f"URL shortening skipped: {e}")
        return None

    def _prepare_link(self, raw_url: str) -> Tuple[str, str]:
        clean = self._clean_url(raw_url)
        short = self._shorten_url(clean)
        display = short or clean
        return display, clean

    def _fmt_time_abbrev(self, s: Optional[str]) -> Optional[str]:
        """Normalize time strings to abbreviated units and strip any extra notes.
        Examples:
          '4 hours (including marination)' -> '4 hr'
          '2.5–3 hours' -> '2.5–3 hr'
          '30 minutes' -> '30 min'
        """
        if not s:
            return None
        try:
            txt = str(s).strip()
            # remove approximation tildes and compress whitespace
            txt = txt.replace('~', ' ').strip()
            # drop parenthetical notes
            import re as _re
            txt = _re.sub(r"\s*\([^)]*\)", "", txt)
            # normalize dashes
            txt = txt.replace('—', '-').replace('–', '-')
            # unify spacing
            txt = ' '.join(txt.split())
            # abbreviate hours/minutes (singular/plural)
            txt = _re.sub(r"\b(hours?|hrs?)\b", "hr", txt, flags=_re.I)
            txt = _re.sub(r"\b(minutes?|mins?)\b", "min", txt, flags=_re.I)
            # ensure ranges keep unit only once when appropriate (e.g., '2-3 hr')
            # If pattern like "(\d+(?:\.\d+)?)\s*[-]\s*(\d+(?:\.\d+)?)\s*(hr|min)"
            m = _re.match(r"^(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)(?:\s*(hr|min))$", txt, flags=_re.I)
            if m:
                a, b, u = m.groups()
                return f"{a}-{b} {u.lower()}"
            return txt
        except Exception:
            return s

    def _infer_servings_from_ingredients(self, ingredients: Optional[List]) -> Optional[str]:
        """Heuristic: infer servings from ingredient quantities.
        - Piece counts (eggs, thighs, breasts, fillets, ribs, chops, drumsticks, tortillas, buns, rolls): use the integer count if 2..12
        - Weight to servings: sum grams (g/kg) and estimate servings ≈ grams/200 (min 1, max 12)
        Returns a string like '4' or None if unknown.
        """
        if not ingredients:
            return None
        import re as _re
        piece_tokens = [
            'egg', 'thigh', 'breast', 'fillet', 'rib', 'chop', 'drumstick',
            'wing', 'tender', 'cutlet', 'steak', 'bao', 'tortilla', 'bun', 'roll', 'pita'
        ]
        piece_max = 0
        grams_total = 0.0

        def _parse_qty(q):
            try:
                # handle fractions like 1/2 or 1 1/2
                q = str(q).strip()
                if ' ' in q and '/' in q:
                    whole, frac = q.split(' ', 1)
                    num, den = frac.split('/', 1)
                    return float(whole) + float(num)/float(den)
                if '/' in q:
                    num, den = q.split('/', 1)
                    return float(num)/float(den)
                return float(q)
            except Exception:
                try:
                    return float(_re.sub(r"[^0-9\.]+", "", q))
                except Exception:
                    return None

        def _consume_item(item):
            nonlocal piece_max, grams_total
            if isinstance(item, dict):
                q = item.get('quantity')
                unit = (item.get('unit') or '').lower()
                name = (item.get('name') or '').lower()
            else:
                s = str(item)
                # crude parse: leading quantity + optional unit + rest
                m = _re.match(r"^\s*([0-9]+(?:\s+[0-9]/[0-9]|/[0-9])?)\s*([A-Za-z]+)?\s+(.*)$", s)
                q = m.group(1) if m else None
                unit = (m.group(2) or '').lower() if m else ''
                name = (m.group(3) or s).lower()

            val = _parse_qty(q) if q is not None else None

            # piece-based heuristic
            if val is not None and 2 <= val <= 12:
                if any(tok in name for tok in piece_tokens):
                    piece_max = max(piece_max, int(round(val)))

            # weight-based heuristic
            if val is not None:
                if unit in ('g', 'gram', 'grams'):
                    grams_total += float(val)
                elif unit in ('kg', 'kilogram', 'kilograms'):
                    grams_total += float(val) * 1000.0

        try:
            for it in ingredients:
                _consume_item(it)
        except Exception:
            pass

        # prefer piece count if reasonable
        if piece_max >= 2:
            return str(piece_max)
        # else derive from grams
        if grams_total > 0:
            est = max(1, min(12, int(round(grams_total / 200.0))))
            return str(est)
        return None

    def _truncate_to_two_lines(self, text: str, style: ParagraphStyle, width: float) -> str:
        """Return a version of `text` that fits within two lines for the given style+width.
        Uses a binary search over character count and appends an ellipsis if truncated."""
        clean = ' '.join((text or '').split())
        if not clean:
            return ''
        # Quick accept: if fits already, return
        p = Paragraph(clean, style)
        _, h = p.wrap(width, 1e6)
        max_h = style.leading * 2 + 0.5
        if h <= max_h:
            return clean
        # Binary search for max chars that fit in 2 lines
        lo, hi = 0, len(clean)
        best = ''
        while lo <= hi:
            mid = (lo + hi) // 2
            candidate = clean[:mid].rstrip()
            # Always try with ellipsis when truncating
            if mid < len(clean):
                candidate = (candidate + '…').rstrip()
            p = Paragraph(candidate, style)
            _, ch = p.wrap(width, 1e6)
            if ch <= max_h:
                best = candidate
                lo = mid + 1
            else:
                hi = mid - 1
        return best or ''

    def _compact_notes(self, recipe_data: Dict, inner_width: float) -> str:
        """Prefer pre-computed compact notes from the upstream LLM call; otherwise collapse
        description+notes into a single string and truncate it to two lines for the footer notes box."""
        # 1) Use compact field if provided by the single LLM call
        compact = ''
        src = recipe_data or {}
        # Prefer explicit compact field if present
        compact = (src.get('notes_compact') or '').strip()
        if compact:
            return self._truncate_to_two_lines(compact, self.styles['Notes'], inner_width)
        # 2) Fall back to combining description + notes
        desc = (src.get('description') or '').strip()
        notes = (src.get('notes') or '').strip()
        combined = ' '.join([s for s in [desc, notes] if s])
        return self._truncate_to_two_lines(combined, self.styles['Notes'], inner_width)

    def generate_pdf(self, recipe_data: Dict, image_path: Optional[str] = None, post_url: Optional[str] = None) -> Tuple[str, bool]:
        try:
            # Get layout version from environment variable
            layout_version = os.getenv("LAYOUT_VERSION", "v2")
            # Check if caching is disabled (useful for testing)
            disable_cache = os.getenv("DISABLE_PDF_CACHE", "false").lower() == "true"
            # --- LOG SETTINGS ---
            logger.info(f"[PDF] LAYOUT_VERSION={layout_version}")
            logger.info(f"[PDF] LAYOUT_CONFIG={os.getenv('LAYOUT_CONFIG')}")
            # --------------------
            if not disable_cache:
                creator = recipe_data.get("source", {}).get("creator", "")
                caption = recipe_data.get("source", {}).get("caption", "")
                from src.agents.pdf_cache import get_post_hash
                post_hash = get_post_hash(caption, creator, layout_version)
                cached_path = self.cache.get(post_hash)
                if cached_path and os.path.exists(cached_path):
                    logger.info(f"Using cached PDF for post_hash {post_hash}")
                    return cached_path, True
            else:
                logger.info("PDF caching disabled via DISABLE_PDF_CACHE environment variable")
                post_hash = None

            logger.info(f"Generating PDF for recipe: {recipe_data.get('title', 'Untitled Recipe')} using template {layout_version}")
            filename = self._get_filename(recipe_data)
            filepath = os.path.join(self.output_dir, filename)
            # Generate PDF based on template version
            if layout_version == "v2":
                if disable_cache:
                    return self._generate_pdf_v2(recipe_data, image_path, post_url, filepath, None, "", "")
                else:
                    return self._generate_pdf_v2(recipe_data, image_path, post_url, filepath, post_hash, creator, caption)
            else:
                if disable_cache:
                    return self._generate_pdf_v1(recipe_data, image_path, post_url, filepath, None, "", "")
                else:
                    return self._generate_pdf_v1(recipe_data, image_path, post_url, filepath, post_hash, creator, caption)
        except Exception as e:
            logger.error(f"Failed to generate PDF: {str(e)}")
            return None, False

    def _generate_pdf_v1(self, recipe_data: Dict, image_path: Optional[str], post_url: Optional[str], filepath: str, post_hash: str, creator: str, caption: str) -> Tuple[str, bool]:
        """Generate PDF using V1 template (original format)"""
        try:
            doc = SimpleDocTemplate(filepath, pagesize=self._get_pagesize(), rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
            elements = []

            # Include image if present
            if image_path and os.path.exists(image_path):
                try:
                    from PIL import Image as PILImage
                    with PILImage.open(image_path) as pil_img:
                        width, height = pil_img.size
                    max_width = doc.width
                    max_height = doc.height * 0.4  # Allow image to use up to 40% of page height
                    scale_factor = min(max_width / width, max_height / height, 1.0)
                    img = RLImage(image_path, width=width * scale_factor, height=height * scale_factor)
                    img.hAlign = 'CENTER'
                    elements.append(img)
                    elements.append(Spacer(1, 8))
                except Exception as img_error:
                    logger.warning(f"Failed to load image into PDF: {img_error}")

            title = recipe_data.get('title', 'Untitled Recipe')
            elements.append(Paragraph(title, self.styles['RecipeTitle']))
            elements.append(Spacer(1, 8))

            description = recipe_data.get('description')
            if description:
                elements.append(Paragraph(description, self.styles['Normal']))
                elements.append(Spacer(1, 8))

            info_elements = self._create_recipe_info_v1(recipe_data, doc.width)
            if info_elements:
                elements.extend(info_elements)
                elements.append(Spacer(1, 8))

            elements.append(Paragraph('Ingredients', self.styles['SectionTitle']))
            elements.append(Spacer(1, 4))
            ingredients = recipe_data.get('ingredients', [])
            if ingredients:
                ingredient_elements = self._create_ingredients_list_v1(ingredients)
                elements.extend(ingredient_elements)
            else:
                elements.append(Paragraph('No ingredients listed', self.styles['Normal']))

            elements.append(Spacer(1, 8))
            elements.append(Paragraph('Instructions', self.styles['SectionTitle']))
            elements.append(Spacer(1, 4))
            instructions = recipe_data.get('instructions', [])
            if instructions:
                instruction_elements = self._create_instructions_list_v1(instructions)
                elements.extend(instruction_elements)
            else:
                elements.append(Paragraph('No instructions listed', self.styles['Normal']))

            elements.append(Spacer(1, 16))
            footer_elements = self._create_footer(recipe_data, post_url)
            elements.extend(footer_elements)

            doc.build(elements)
            if post_hash:
                self.cache.set(post_hash, creator, caption, recipe_data, filepath)
                logger.info(f"PDF cache set for post_hash {post_hash}")
            logger.info(f"PDF generated successfully: {filepath}")
            return filepath, False
        except Exception as e:
            logger.error(f"Failed to generate V1 PDF: {str(e)}")
            return None, False
    
    def _generate_pdf_v2(self, recipe_data: Dict, image_path: Optional[str], post_url: Optional[str], filepath: str, post_hash: str, creator: str, caption: str) -> Tuple[str, bool]:
        """Generate PDF using V2 template with footer at bottom"""
        try:
            # Store data for onPage callback - THIS IS CRITICAL
            self._temp_recipe_data = recipe_data

            # Standard document with normal margins
            doc = SimpleDocTemplate(
                filepath,
                pagesize=self._get_pagesize(),
                rightMargin=40,
                leftMargin=40,
                topMargin=35,
                bottomMargin=90  # Reserve space for footer
            )

            elements = []

            # Header section
            header_table = self._create_header_section_v2(recipe_data, image_path, doc.width)
            if header_table:
                elements.append(header_table)
                elements.append(Spacer(1, 20))

            # Two-column content
            content_table = self._create_two_column_content_v2(recipe_data, doc.width)
            if content_table:
                elements.append(content_table)

            # Build the document with correct onPage callbacks for footer
            doc.build(
                elements,
                onFirstPage=self._add_footer_on_page,
                onLaterPages=self._add_footer_on_page,
            )

            # Clean up
            self._temp_recipe_data = None

            # Cache if needed
            if post_hash:
                self.cache.set(post_hash, creator, caption, recipe_data, filepath)
                self.cache.save()
                logger.info(f"PDF cache set for post_hash {post_hash}")

            logger.info(f"PDF generated successfully: {filepath}")
            return filepath, False

        except Exception as e:
            logger.error(f"Failed to generate V2 PDF: {str(e)}")
            return None, False

    def _add_footer_on_page(self, canvas, doc):
        """Draw footer directly on canvas at bottom of page"""
        if not hasattr(self, '_temp_recipe_data') or not self._temp_recipe_data:
            logger.warning("No recipe data for footer")
            return

        canvas.saveState()
        try:
            page_width = doc.pagesize[0]

            # Compute white card geometry from content first
            band_pad_v = 14  # vertical padding inside grey band
            band_bg = colors.HexColor('#F3F4F6')

            # Build compact notes text and measure paragraphs with inner width
            card_margin_lr = doc.leftMargin + doc.rightMargin
            box_width = page_width - card_margin_lr
            inner_pad = 16
            box_inner_width = box_width - 2 * inner_pad

            compact = self._compact_notes(self._temp_recipe_data, box_inner_width)

            if compact:
                title_para = Paragraph("Chef's Notes", self.styles['NotesTitle'])
                body_para  = Paragraph(compact,         self.styles['Notes'])

                # Measure natural heights (use large height so wrap isn't constrained)
                tw, th = title_para.wrap(box_inner_width, 1e6)
                gap = 6
                bw, bh = body_para.wrap(box_inner_width, 1e6)

                # Card height fits title + gap + body + vertical padding
                box_height = max(52, int(th + gap + bh + 2 * inner_pad))
                # Grey band height = card height + band vertical padding top+bottom
                band_height = box_height + 2 * band_pad_v

                # Draw grey band full-bleed across the page bottom
                canvas.setFillColor(band_bg)
                canvas.rect(0, 0, page_width, band_height, stroke=0, fill=1)

                # Position white card inside band (not centered; pinned to band padding)
                box_x = doc.leftMargin
                box_y = band_pad_v

                canvas.setFillColor(colors.white)
                canvas.setStrokeColor(colors.HexColor('#E0E0E0'))
                canvas.setLineWidth(1)
                canvas.roundRect(box_x, box_y, box_width, box_height, 8, stroke=1, fill=1)

                # Draw paragraphs top-down with padding
                content_left = box_x + inner_pad
                content_top  = box_y + box_height - inner_pad

                title_y = content_top - th
                title_para.drawOn(canvas, content_left, title_y)

                body_y = title_y - gap - bh
                if body_y < (box_y + inner_pad):
                    body_y = box_y + inner_pad
                body_para.drawOn(canvas, content_left, body_y)

            else:
                # No notes content; draw a minimal grey band so layout remains consistent
                band_height = max(50, int(doc.bottomMargin) - 10)
                canvas.setFillColor(band_bg)
                canvas.rect(0, 0, page_width, band_height, stroke=0, fill=1)
        except Exception as e:
            logger.error(f"Footer draw failed: {e}")
        canvas.restoreState()

    def _create_notes_section_raw(self, recipe_data, page_width):
        """Create the grey band with notes - simplified for edge-to-edge rendering"""
        try:
            # Skip if already in header
            if recipe_data.get('_notes_placed_in_header'):
                return None
                
            from reportlab.platypus import Table, TableStyle
            
            # Create the notes content
            card_width = page_width - 80  # White card width (with margins)
            inner_width = card_width - 32  # Internal padding
            
            notes_elements = []
            compact_text = self._compact_notes(recipe_data, inner_width)
            
            if compact_text:
                notes_elements.append(Paragraph("Chef's Notes", self.styles['NotesTitle']))
                notes_elements.append(Spacer(1, 6))
                notes_elements.append(Paragraph(compact_text, self.styles['Notes']))
            else:
                return None
            
            # Create inner table for notes content
            notes_table = Table([[notes_elements]], colWidths=[inner_width])
            notes_table.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('LEFTPADDING', (0, 0), (-1, -1), 0),
                ('RIGHTPADDING', (0, 0), (-1, -1), 0),
                ('TOPPADDING', (0, 0), (-1, -1), 0),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
            ]))
            
            # Use RoundedTable for the rounded corners (you already have this class!)
            rounded = RoundedTable(
                notes_table,
                width=card_width,
                padding=16,
                radius=8,  # Rounded corners
                bg=colors.white,
                stroke=colors.HexColor('#E0E0E0'),
                stroke_width=1
            )

            # Wrap in grey background table for edge-to-edge effect
            outer_table = Table([[rounded]], colWidths=[page_width])
            outer_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F3F4F6')),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('LEFTPADDING', (0, 0), (-1, -1), 40),  # Match document margins
                ('RIGHTPADDING', (0, 0), (-1, -1), 40),
                ('TOPPADDING', (0, 0), (-1, -1), 14),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 14),
            ]))
            
            return outer_table
            
        except Exception as e:
            logger.error(f"Error creating notes section: {e}")
            return None
    
    def _create_recipe_info_v1(self, recipe_data, page_width):
        """Create compact single-row stats strip for V1 to match V2 style."""
        try:
            def _fmt(v, default='—'):
                if v is None:
                    return default
                s = str(v).strip()
                return s if s else default

            prep_time = _fmt(recipe_data.get('prep_time', '—'))
            cook_time = _fmt(recipe_data.get('cook_time', '—'))
            servings  = _fmt(recipe_data.get('servings', '—'))
            likes_val = recipe_data.get('likes')
            views_val = recipe_data.get('views')
            likes     = _fmt(likes_val if likes_val is not None else views_val, '—')

            c1 = self._icon_text_cell('timer.png',  f"{prep_time} (Prep)")
            c2 = self._icon_text_cell('flame.png',  f"{cook_time} (Cook)")
            c3 = self._icon_text_cell('plate.png',  f"{servings} (Feeds)")
            c4 = self._icon_text_cell('heart.png',  f"{likes} (Likes)")

            tbl = Table([[c1, c2, c3, c4]], colWidths=[page_width/4.0]*4)
            tbl.setStyle(TableStyle([
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                ('LEFTPADDING', (0,0), (-1,-1), 0),
                ('RIGHTPADDING', (0,0), (-1,-1), 0),
                ('TOPPADDING', (0,0), (-1,-1), 6),
                ('BOTTOMPADDING', (0,0), (-1,-1), 6),
                ('LINEABOVE', (0,0), (-1,0), 0.5, colors.HexColor('#E5E7EB')),
                ('LINEBELOW', (0,0), (-1,0), 0.5, colors.HexColor('#E5E7EB')),
            ]))
            return [tbl]
        except Exception as e:
            logger.error(f"V1 stats strip failed: {e}")
            return []
    
    def _create_ingredients_list_v1(self, ingredients):
        """Create a formatted list of ingredients without bullets"""
        elements = []

        if ingredients and isinstance(ingredients[0], dict) and 'section' in ingredients[0]:
            # Sectioned ingredients
            for section in ingredients:
                section_title = section.get('section', '').strip()
                items = section.get('items', [])
                if section_title:
                    elements.append(Paragraph(section_title, self.styles['SectionTitle']))
                for item in items:
                    quantity = item.get('quantity', '')
                    unit = item.get('unit', '')
                    name = item.get('name', '')

                    if quantity and unit:
                        text = f"{quantity} {unit} {name}"
                    elif quantity:
                        text = f"{quantity} {name}"
                    else:
                        text = name

                    elements.append(Paragraph(text, self.styles['IngredientItem']))
                elements.append(Spacer(1, 4))
        else:
            # Flat list
            for ingredient in ingredients:
                if isinstance(ingredient, dict):
                    quantity = ingredient.get('quantity', '')
                    unit = ingredient.get('unit', '')
                    name = ingredient.get('name', '')
                    if quantity and unit:
                        ingredient_text = f"{quantity} {unit} {name}"
                    elif quantity:
                        ingredient_text = f"{quantity} {name}"
                    else:
                        ingredient_text = name
                else:
                    ingredient_text = ingredient

                elements.append(Paragraph(ingredient_text, self.styles['IngredientItem']))

        return elements
    
    def _create_instructions_list_v1(self, instructions):
        """Create a formatted list of instruction steps"""
        elements = []
        
        for i, step in enumerate(instructions, 1):
            step_text = f"{i}. {step}"
            elements.append(Paragraph(step_text, self.styles['InstructionItem']))
        
        return elements
    
    def _create_footer(self, recipe_data, post_url=None):
        """Create footer section with source information"""
        elements = []
        src = recipe_data.get('source', {}) if isinstance(recipe_data, dict) else {}
        url_raw = src.get('url') or post_url or ''
        clean = self._clean_url(url_raw)
        if clean:
            elements.append(Paragraph(f'Source: Instagram - <a href="{clean}" color="gray">{clean}</a>', self.styles['Footer']))
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        elements.append(Paragraph(f"Generated on {timestamp}", self.styles['Footer']))
        return elements
    
    def _get_filename(self, recipe_data):
        """Generate a filename for the PDF"""
        title = recipe_data.get('title', 'Untitled Recipe')
        clean_title = ''.join(c if c.isalnum() or c.isspace() else '_' for c in title)
        clean_title = clean_title.replace(' ', '_')
        
        if len(clean_title) > 50:
            clean_title = clean_title[:50]
        
        timestamp = int(time.time())
        
        return f"{clean_title}_{timestamp}.pdf"

    def _create_header_section_v2(self, recipe_data, image_path, page_width):
        """Create header section with image, recipe info, and inline stats (V2 template)"""
        try:
            # Left column: Square Image
            left_elements = []
            if image_path and os.path.exists(image_path):
                try:
                    from PIL import Image as PILImage
                    import tempfile
                    # Crop to square (centered)
                    with PILImage.open(image_path) as pil_img:
                        width, height = pil_img.size
                        min_dimension = min(width, height)
                        left = (width - min_dimension) // 2
                        top = 0  # align to top for vertical alignment
                        right = left + min_dimension
                        bottom = top + min_dimension
                        cropped_img = pil_img.crop((left, top, right, bottom))
                        temp_img_path = tempfile.mktemp(suffix='.jpg')
                        cropped_img.save(temp_img_path, 'JPEG', quality=95)
                    # Use cropped square image in PDF
                    available_width = page_width
                    left_col_width = available_width * 0.4
                    img_size = left_col_width  # Square: width and height
                    img = RLImage(temp_img_path, width=img_size, height=img_size)
                    left_elements.append(img)
                except Exception as img_error:
                    logger.warning(f"Failed to load header image: {img_error}")

            # Right column: Recipe info
            right_elements = []
            title = recipe_data.get('title', 'Untitled Recipe')
            right_elements.append(Paragraph(title, self.styles['RecipeTitle']))

            # (Subtitle moved to notes section; keep header tighter)
            right_elements.append(Spacer(1, 2))

            source = recipe_data.get('source', {})
            creator = source.get('creator', '')
            ig_handle = source.get('instagram_handle', '') or "chef_marco"
            # Single meta line to match template: "Chef Marco Antonelli @chef_marco"
            meta_line = f"Chef {creator} @{ig_handle}" if creator else f"Chef Marco Antonelli @{ig_handle}"
            right_elements.append(self._icon_text_cell('chef-hat.png', meta_line, style_name='ChefInfo', icon_px=12))
            right_elements.append(Spacer(1, 6))

            url = source.get('url', '')
            if url:
                clean = self._clean_url(url)
                url_text = f'<a href="{clean}" color="blue">{clean}</a>'
                right_elements.append(self._icon_text_cell('external-link.png', url_text, style_name='ChefInfo', icon_px=12))

            # Inline stats below meta/link with a small gap
            right_elements.append(Spacer(1, 18))
            stats_para = self._create_inline_stats(recipe_data)
            right_elements.append(stats_para)

            # Try to tuck Chef's Notes into the remaining vertical space under the stats (within the image's square height)
            MIN_NOTES = 60  # minimum height to render a compact notes block here
            try:
                # Compute used height of right column so far
                used_h = 0
                # Right column width matches right_col_width below; compute it here
                available_width = page_width
                left_col_width = available_width * 0.4
                right_col_width = available_width * 0.6
                for f in right_elements:
                    try:
                        _, h = f.wrap(right_col_width, 10000)
                    except Exception:
                        # Some flowables (like Tables of mixed items) might need a second wrap; ignore failures
                        h = 0
                    used_h += h
                # Image is a square with side = left_col_width
                img_size = left_col_width
                free_h = max(0, img_size - used_h)

                if free_h >= MIN_NOTES and recipe_data.get('_tuck_notes_in_header'):
                    # Build a compact notes block (description + notes) and shrink to fit if needed
                    compact = []
                    desc = recipe_data.get('description')
                    notes_txt = recipe_data.get('notes')
                    if desc or notes_txt:
                        compact.append(Paragraph("Chef's Notes", self.styles['NotesTitle']))
                        if desc:
                            compact.append(Paragraph(' '.join(str(desc).split()), self.styles['RecipeDescription']))
                            compact.append(Spacer(1, 4))
                        if notes_txt:
                            compact.append(Paragraph(notes_txt, self.styles['Notes']))
                        # Use inner content width (minus rounded padding) to guarantee wrapping
                        pad = 12
                        kif = KeepInFrame(
                            right_col_width - 2*pad,            # inner width
                            max(0, free_h - 2*pad),             # inner height
                            compact,
                            mode='shrink'
                        )
                        # Wrap in rounded background to match template
                        inner_tbl = Table([[kif]], colWidths=[right_col_width - 2*pad])
                        inner_tbl.setStyle(TableStyle([
                            ('VALIGN', (0,0), (-1,-1), 'TOP'),
                            ('LEFTPADDING', (0,0), (-1,-1), 0),
                            ('RIGHTPADDING', (0,0), (-1,-1), 0),
                            ('TOPPADDING', (0,0), (-1,-1), 0),
                            ('BOTTOMPADDING', (0,0), (-1,-1), 0),
                        ]))
                        rounded = RoundedTable(
                            inner_tbl,
                            width=right_col_width,
                            padding=pad,
                            radius=6,
                            bg=self.notes_bg,
                            stroke=colors.HexColor('#E0E0E0'),
                            stroke_width=1
                        )
                        # Pre-wrap to know its height so we can bottom-align with the image square
                        try:
                            _, rounded_h = rounded.wrap(right_col_width, free_h)
                        except Exception:
                            rounded_h = min(free_h, img_size)
                        # Spacer to push the notes block down so its bottom aligns with image bottom; subtract a few points to avoid rounding spillover
                        push_down = max(0, img_size - (used_h + rounded_h) - 12)
                        if push_down > 0:
                            right_elements.append(Spacer(1, push_down))
                        right_elements.append(rounded)

                        # Mark so the bottom notes section doesn't duplicate
                        recipe_data['_notes_placed_in_header'] = True
            except Exception as _notes_err:
                logger.warning(f"Header-notes placement skipped: {_notes_err}")

            # Create table with image left, info right
            if left_elements and right_elements:
                available_width = page_width
                left_col_width = available_width * 0.4
                right_col_width = available_width * 0.6
                # Wrap the right column elements in KeepInFrame for vertical centering to the image
                kif_right = KeepInFrame(
                    right_col_width,  # width available for right column
                    img_size,         # match the image height for vertical alignment
                    right_elements,   # list of flowables for the right column
                    mode='shrink',    # shrink to fit if needed
                    hAlign='LEFT',
                    vAlign='MIDDLE'   # vertically center relative to image
                )
                table_data = [[left_elements, [kif_right]]]
                col_widths = [left_col_width, right_col_width]
                table = Table(table_data,
                            colWidths=[left_col_width, right_col_width],
                            rowHeights=[img_size])
                table.setStyle(TableStyle([
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    # Increase gutter between image (col 0) and text (col 1)
                    ('RIGHTPADDING', (0, 0), (0, 0), 12),
                    ('LEFTPADDING',  (1, 0), (1, 0), 12),  # match right-column body padding
                    ('LEFTPADDING',  (0, 0), (0, 0), 0),
                    ('RIGHTPADDING', (1, 0), (1, 0), 0),
                    ('TOPPADDING', (0, 0), (-1, -1), 0),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
                ]))
                return table
            elif right_elements:
                if len(right_elements) == 1:
                    return right_elements[0]
                else:
                    table_data = [[right_elements]]
                    table = Table(table_data, colWidths=[page_width])
                    table.setStyle(TableStyle([
                        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                        ('LEFTPADDING', (0, 0), (-1, -1), 0),
                        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
                        ('TOPPADDING', (0, 0), (-1, -1), 0),
                        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
                    ]))
                    return table
        except Exception as e:
            logger.error(f"Error creating header section: {e}")
        return None

    def _create_inline_stats(self, recipe_data):
        """Create a compact single-row stats strip with normalized units and inferred servings."""
        try:
            def _fmt(v, default='—'):
                if v is None:
                    return default
                s = str(v).strip()
                return s if s else default

            # Prep/Cook: abbreviate units and strip any extra parentheses
            prep_time_raw = recipe_data.get('prep_time')
            cook_time_raw = recipe_data.get('cook_time')
            prep_time = self._fmt_time_abbrev(prep_time_raw) or '15 min'
            cook_time = self._fmt_time_abbrev(cook_time_raw) or '25 min'

            # Servings: use provided, else infer from ingredients
            servings_raw = recipe_data.get('servings')
            servings = None
            if servings_raw:
                servings = str(servings_raw).strip()
            if not servings or servings == '—':
                servings_inf = self._infer_servings_from_ingredients(recipe_data.get('ingredients', []))
                if servings_inf:
                    servings = servings_inf
                    # persist into data so footer/header can reuse if needed
                    recipe_data['servings'] = servings
            servings = servings or '—'

            # Likes/Views
            likes_val = recipe_data.get('likes')
            views_val = recipe_data.get('views')
            likes = _fmt(likes_val if likes_val is not None else views_val, '—')
            likes_label = 'Likes' if (likes_val is not None) else ('Views' if (views_val is not None) else 'Likes')

            # Create icon cells with strict labels '(Prep)' and '(Cook)'
            c1 = self._icon_text_cell('timer.png', f"{prep_time} (Prep)", style_name='StatsInline', icon_px=10)
            c2 = self._icon_text_cell('flame.png', f"{cook_time} (Cook)", style_name='StatsInline', icon_px=10)
            c3 = self._icon_text_cell('plate.png', f"{servings} (Feeds)", style_name='StatsInline', icon_px=10)
            c4 = self._icon_text_cell('heart.png', f"{likes} ({likes_label})", style_name='StatsInline', icon_px=10)

            outer = Table([[c1, c2, c3, c4]], colWidths=[None, None, None, None])
            outer.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('LEFTPADDING', (0, 0), (-1, -1), 2),
                ('RIGHTPADDING', (0, 0), (-1, -1), 8),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('LINEABOVE', (0, 0), (-1, 0), 0.5, colors.HexColor('#E5E7EB')),
                ('LINEBELOW', (0, 0), (-1, 0), 0.5, colors.HexColor('#E5E7EB')),
            ]))
            return outer

        except Exception as e:  # Fallback path preserved
            logger.error(f"Error creating inline stats: {e}")
            try:
                prep = self._fmt_time_abbrev(recipe_data.get('prep_time')) or '15 min'
                cook = self._fmt_time_abbrev(recipe_data.get('cook_time')) or '25 min'
                serv = recipe_data.get('servings') or self._infer_servings_from_ingredients(recipe_data.get('ingredients', [])) or '—'
                like = _fmt(recipe_data.get('likes') or recipe_data.get('views'), '—')
                line = f"{prep} (Prep) · {cook} (Cook) · {serv} (Feeds) · {like} (Views)"
                return Paragraph(line, self.styles['StatsInline'])
            except Exception:
                return Paragraph('', self.styles['StatsInline'])

    def _number_badge(self, n: int, diameter: int = 14):
        """Return a small circular number badge as a Drawing for table cell usage.
        Default diameter reduced ~20% from 16 -> 13.
        """
        d = Drawing(diameter, diameter)
        r = diameter / 2.0
        d.add(Circle(r, r, r, fillColor=colors.black, strokeColor=colors.black))
        # Font size relative to badge size for good fit
        fs = max(7, int(round(diameter * 0.55)))
        # Vertically center-ish the number
        y = r - (fs * 0.35)
        d.add(String(r, y, str(n), fontName=self.badge_bold_font, fontSize=fs, fillColor=colors.white, textAnchor='middle'))
        return d

    def _create_two_column_content_v2(self, recipe_data, page_width):
        """Create two-column layout with dynamic sizing to fit one page"""
        try:
            from reportlab.platypus import KeepInFrame
            
            # Calculate available height for the middle section
            # This is approximate - you'll need to adjust based on your header/footer heights
            page_height = self._get_pagesize()[1]
            header_height = 200  # Approximate height of header section
            footer_height = 90   # Height reserved for footer
            available_height = page_height - header_height - footer_height - 40  # Extra margin
            
            # Calculate column widths
            available_width = page_width
            left_col_width = available_width * 0.4
            right_col_width = available_width * 0.6
            
            # Create content with normal sizing first
            left_elements = self._create_ingredients_column(recipe_data, left_col_width)
            right_elements = self._create_directions_column(recipe_data, right_col_width)
            
            # Wrap each column in KeepInFrame to force fit
            left_kif = KeepInFrame(
                left_col_width,
                available_height,
                left_elements,
                mode='shrink',  # This will shrink content to fit
                vAlign='TOP'
            )
            
            right_kif = KeepInFrame(
                right_col_width,
                available_height,
                right_elements,
                mode='shrink',
                vAlign='TOP'
            )
            
            # Create the two-column table
            table = Table([[left_kif, right_kif]], colWidths=[left_col_width, right_col_width])
            table.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('LEFTPADDING', (0, 0), (0, -1), 0),
                ('RIGHTPADDING', (0, 0), (0, -1), 12),
                ('LEFTPADDING', (1, 0), (1, -1), 12),
                ('RIGHTPADDING', (1, 0), (1, -1), 0),
                ('TOPPADDING', (0, 0), (-1, -1), 12),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
                ('BACKGROUND', (0, 0), (-1, -1), colors.white),
            ]))
            return table
            
        except Exception as e:
            logger.error(f"Error creating two-column content: {e}")
            return None

    def _create_ingredients_column(self, recipe_data, col_width):
        """Create ingredients column elements"""
        elements = []
        elements.append(Paragraph('Ingredients', self.styles['SectionTitleCentered']))
        elements.append(Spacer(1, 6))
        
        ingredients = recipe_data.get('ingredients', [])
        if ingredients:
            # For very long lists, use tighter spacing
            ingredient_count = len(ingredients)
            if ingredient_count > 15:
                # Create a custom style with smaller font and tighter leading
                tight_style = ParagraphStyle(
                    'TightIngredient',
                    parent=self.styles['IngredientItem'],
                    fontSize=9,  # Smaller font
                    leading=11,  # Tighter line spacing
                    spaceAfter=2  # Less space between items
                )
                style_to_use = tight_style
            else:
                style_to_use = self.styles['IngredientItem']
                
            for ingredient in ingredients:
                if isinstance(ingredient, dict):
                    quantity = ingredient.get('quantity', '')
                    unit = ingredient.get('unit', '')
                    name = ingredient.get('name', '')
                    if quantity and unit:
                        ingredient_text = f'{quantity} {unit} {name}'
                    elif quantity:
                        ingredient_text = f'{quantity} {name}'
                    else:
                        ingredient_text = name
                else:
                    ingredient_text = ingredient
                    
                elements.append(Paragraph(ingredient_text, style_to_use))
        else:
            elements.append(Paragraph('No ingredients listed', self.styles['Normal']))
        
        return elements

    def _create_directions_column(self, recipe_data, col_width):
        """Create directions column elements"""
        elements = []
        elements.append(Paragraph('Directions', self.styles['SectionTitleCentered']))
        elements.append(Spacer(1, 6))
        
        instructions = recipe_data.get('instructions', [])
        if instructions:
            instruction_count = len(instructions)
            
            # For very long instruction lists, use tighter spacing
            if instruction_count > 8:
                tight_style = ParagraphStyle(
                    'TightInstruction',
                    parent=self.styles['InstructionItem'],
                    fontSize=9,
                    leading=11,
                    spaceAfter=6
                )
                badge_w = 20  # Slightly smaller badge width
                bottom_padding = 6  # Less space between rows
            else:
                tight_style = self.styles['InstructionItem']
                badge_w = 22
                bottom_padding = 10
                
            rows = []
            for i, step in enumerate(instructions, 1):
                badge = self._number_badge(i, diameter=13 if instruction_count > 8 else 14)
                para = Paragraph(step, tight_style)
                rows.append([badge, para])
                
            steps_table = Table(rows, colWidths=[badge_w, col_width - badge_w])
            steps_table.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('LEFTPADDING', (0, 0), (0, -1), 0),
                ('RIGHTPADDING', (0, 0), (0, -1), 0),
                ('LEFTPADDING', (1, 0), (1, -1), 5),
                ('RIGHTPADDING', (1, 0), (1, -1), 0),
                ('TOPPADDING', (0, 0), (-1, -1), 0),
                ('BOTTOMPADDING', (0, 0), (-1, -1), bottom_padding),
            ]))
            elements.append(steps_table)
        else:
            elements.append(Paragraph('No instructions listed', self.styles['Normal']))
        
        return elements

    def _create_notes_section(self, recipe_data, page_width):
        """Create notes section with rounded rectangle background"""
        try:
            # Skip if header already consumed the notes block
            if recipe_data.get('_notes_placed_in_header'):
                return None
            notes_elements = []
            has_any = False
            # Title will be added only if we end up with content

            # Build compact 2-line max content for notes box
            card_width = page_width - 40
            inner_width = card_width - 2*16  # must match RoundedTable padding
            compact_text = self._compact_notes(recipe_data, inner_width)
            if compact_text:
                has_any = True
                notes_elements.append(Paragraph(compact_text, self.styles['Notes']))

            if not has_any:
                return None
            # Add a lightweight title only when content exists
            notes_elements.insert(0, Spacer(1, 6))
            notes_elements.insert(0, Paragraph("Chef's Notes", self.styles['NotesTitle']))

            # Wrap notes in a table with rounded rectangle styling
            notes_table_data = [[notes_elements]]
            notes_table = Table(notes_table_data, colWidths=[inner_width])
            notes_table.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('TOPPADDING', (0, 0), (-1, -1), 0),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
                ('LEFTPADDING', (0, 0), (-1, -1), 0),
                ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ]))
            rounded = RoundedTable(
                notes_table,
                width=card_width,  # white card width
                padding=16,
                bg=colors.white,
                stroke=colors.HexColor('#E0E0E0'),
                stroke_width=1
            )
            band = FooterBand(
                rounded,
                width=page_width,
                band_bg=colors.HexColor('#F3F4F6'),
                band_pad_h=20,
                band_pad_v=14,
                child_width=card_width,
            )
            return band
        except Exception as e:
            logger.error(f"Error creating notes section: {e}")
        return None