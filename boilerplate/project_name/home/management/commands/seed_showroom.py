"""
Seed a theme showroom for SUM Platform client projects.

This management command is intended to run inside any generated client project
(`sum init <client> --theme <theme_slug>`), creating a predictable showroom
site tree and navigation settings so theme development can start immediately.

It creates:
- A HomePage (client-owned model) and sets it as the default Wagtail Site root
- A StandardPage showroom (optional) + a Contact StandardPage
- A ServiceIndexPage and two ServicePage children
- A "Kitchen Sink" page with all blocks
- Legal pages (Terms, Privacy, Cookies) with legal section blocks
- Example content that showcases *all* blocks available in sum_core.PageStreamBlock,
  spread across multiple pages (not all on one page)
- Branding SiteSettings and Navigation (HeaderNavigation / FooterNavigation)

Usage:
    python manage.py seed_showroom
    python manage.py seed_showroom --clear
    python manage.py seed_showroom --profile starter
    python manage.py seed_showroom --hostname localhost --port 8000
    python manage.py seed_showroom --homepage-model home.HomePage
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from io import BytesIO
from typing import Any

from django.apps import apps
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandParser
from django.db import transaction
from sum_core.blocks import PageStreamBlock
from sum_core.branding.models import SiteSettings
from sum_core.navigation.cache import invalidate_nav_cache
from sum_core.navigation.models import FooterNavigation, HeaderNavigation
from sum_core.pages import ServiceIndexPage, ServicePage, StandardPage
from wagtail.models import Page, Site

PILImage: Any | None
try:
    from PIL import Image as PILImage
except Exception:  # pragma: no cover
    PILImage = None


@dataclass(frozen=True)
class _ShowroomSlugs:
    home: str = "showroom-home"
    showroom: str = "showroom"
    contact: str = "contact"
    services: str = "services"
    service_one: str = "solar-installation"
    service_two: str = "roofing"
    kitchen_sink: str = "kitchen-sink"
    terms: str = "terms"
    privacy: str = "privacy"
    cookies: str = "cookies"


PROFILE_STARTER = "starter"
PROFILE_SHOWROOM = "showroom"
VALID_PROFILES = {PROFILE_STARTER, PROFILE_SHOWROOM}


class Command(BaseCommand):
    help = "Create a theme showroom site tree, blocks, and navigation."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Delete existing showroom pages (by slug) before re-seeding.",
        )
        parser.add_argument(
            "--profile",
            choices=sorted(VALID_PROFILES),
            default=PROFILE_SHOWROOM,
            help="Seed profile to apply (starter or showroom).",
        )
        parser.add_argument(
            "--hostname",
            default=None,
            help="Set the default Site hostname (defaults to existing or 'localhost').",
        )
        parser.add_argument(
            "--port",
            type=int,
            default=None,
            help="Set the default Site port (defaults to existing or 8000).",
        )
        parser.add_argument(
            "--homepage-model",
            default=None,
            help=(
                "Override HomePage model as 'app_label.ModelName' "
                "(defaults to first installed HomePage)."
            ),
        )

    @transaction.atomic
    def handle(self, *args: Any, **options: Any) -> None:
        profile = (options.get("profile") or PROFILE_STARTER).lower()
        if profile not in VALID_PROFILES:
            self.stdout.write(
                self.style.ERROR(
                    f"Unknown profile '{profile}'. Use one of: {', '.join(sorted(VALID_PROFILES))}."
                )
            )
            return

        slugs = _ShowroomSlugs()

        home_page_model = self._resolve_home_page_model(options.get("homepage_model"))
        if home_page_model is None:
            self.stdout.write(
                self.style.ERROR(
                    "Could not find a HomePage model. Ensure your client 'home' app is in INSTALLED_APPS."
                )
            )
            return
        legal_page_model = self._resolve_legal_page_model()

        root = Page.get_first_root_node()
        site = self._get_or_create_default_site(
            options.get("hostname"), options.get("port"), root
        )

        if options.get("clear"):
            self._clear_showroom(
                site=site, slugs=slugs, home_page_model=home_page_model
            )

        # Pages
        # NOTE: We do not blindly grab the first HomePage anymore. We check for our specific slug.
        home = self._get_or_create_homepage(
            site=site, root=root, home_page_model=home_page_model, slugs=slugs
        )
        contact = self._get_or_create_standard_page(
            parent=home, title="Contact", slug=slugs.contact
        )
        showroom = None
        kitchen_sink = None
        if profile == PROFILE_SHOWROOM:
            showroom = self._get_or_create_standard_page(
                parent=home, title="Showroom", slug=slugs.showroom
            )
            kitchen_sink = self._get_or_create_standard_page(
                parent=home, title="Kitchen Sink", slug=slugs.kitchen_sink
            )
        services_index = self._get_or_create_services_index(
            parent=home, title="Services", slug=slugs.services
        )
        service_one = self._get_or_create_service_page(
            parent=services_index,
            title="Solar Installation",
            slug=slugs.service_one,
            short_description="Premium solar installs with clean, modern finishing.",
        )
        service_two = self._get_or_create_service_page(
            parent=services_index,
            title="Roofing",
            slug=slugs.service_two,
            short_description="Durable, weather-ready roofing from a trusted local team.",
        )
        terms = self._get_or_create_legal_page(
            parent=home, title="Terms", slug=slugs.terms, page_model=legal_page_model
        )
        privacy = self._get_or_create_legal_page(
            parent=home,
            title="Privacy",
            slug=slugs.privacy,
            page_model=legal_page_model,
        )
        cookies = self._get_or_create_legal_page(
            parent=home,
            title="Cookies",
            slug=slugs.cookies,
            page_model=legal_page_model,
        )

        # Media (placeholder images)
        images = self._get_or_create_showroom_images()

        if profile == PROFILE_STARTER:
            home.title = "Starter Home"
            home.body = self._build_starter_home_stream(
                images=images, contact_page=contact
            )
            home.intro = (
                "<p>This is a seeded starter homepage for SUM Platform. "
                "Replace the placeholder copy with your client messaging.</p>"
            )
        else:
            home.title = "Theme Showroom"
            home.body = self._build_home_stream(images=images, contact_page=contact)
            home.intro = (
                "<p>This is a seeded theme showroom for SUM Platform. "
                "Swap themes with <code>sum init ... --theme</code> and re-run this command.</p>"
            )
        home.save_revision().publish()

        if showroom is not None:
            showroom.body = self._build_showroom_stream(
                images=images,
                services_index=services_index,
                service_one=service_one,
                contact_page=contact,
            )
            showroom.save_revision().publish()

        # Kitchen Sink - All blocks in one place
        if kitchen_sink is not None:
            kitchen_sink.body = self._build_kitchen_sink_stream(
                images=images,
                services_index=services_index,
                service_one=service_one,
                contact_page=contact,
            )
            kitchen_sink.save_revision().publish()

        services_index.intro = self._build_services_index_intro_stream(images=images)
        services_index.save_revision().publish()

        service_one.featured_image_id = images.service_featured_one_id
        service_one.body = self._build_service_page_stream(
            images=images, page=service_one, contact_page=contact
        )
        service_one.save_revision().publish()

        service_two.featured_image_id = images.service_featured_two_id
        service_two.body = self._build_service_page_stream(
            images=images, page=service_two, contact_page=contact
        )
        service_two.save_revision().publish()

        contact.body = self._build_contact_stream(images=images)
        contact.save_revision().publish()

        terms_intro, terms_sections = self._build_terms_sections()
        self._apply_legal_page_content(
            terms,
            heading="Terms & Conditions",
            intro=terms_intro,
            sections=terms_sections,
        )

        privacy_intro, privacy_sections = self._build_privacy_sections()
        self._apply_legal_page_content(
            privacy,
            heading="Privacy Notice",
            intro=privacy_intro,
            sections=privacy_sections,
        )

        cookies_intro, cookies_sections = self._build_cookie_sections()
        self._apply_legal_page_content(
            cookies,
            heading="Cookie Policy",
            intro=cookies_intro,
            sections=cookies_sections,
        )

        # Site settings (branding + navigation)
        self._seed_branding(
            site=site,
            images=images,
            terms=terms,
            privacy=privacy,
            cookies=cookies,
        )
        self._seed_navigation(
            site=site,
            home=home,
            contact=contact,
            services_index=services_index,
            service_one=service_one,
            service_two=service_two,
            terms=terms,
            privacy=privacy,
            cookies=cookies,
            showroom=showroom,
            kitchen_sink=kitchen_sink,
        )
        invalidate_nav_cache(site.id)

        self.stdout.write(self.style.SUCCESS(f"✓ Showroom seeded ({profile})"))
        self.stdout.write(f"  - Home: / (Wagtail site root -> {home.title})")
        if showroom is not None:
            self.stdout.write(f"  - Showroom: {showroom.url}")
        if kitchen_sink is not None:
            self.stdout.write(f"  - Kitchen Sink: {kitchen_sink.url}")
        self.stdout.write(f"  - Services: {services_index.url}")
        self.stdout.write(f"  - Contact: {contact.url}")
        self.stdout.write(f"  - Terms: {terms.url}")
        self.stdout.write(f"  - Privacy: {privacy.url}")
        self.stdout.write(f"  - Cookies: {cookies.url}")

    # -----------------------------------------------------------------------------
    # Model resolution / site helpers
    # -----------------------------------------------------------------------------

    def _resolve_home_page_model(self, dotted: str | None) -> Any | None:
        """
        Resolve the client-owned HomePage model.

        Strategy:
        - If --homepage-model is provided (app_label.ModelName), use it
        - Otherwise, prefer any app labeled 'home' that exposes HomePage
        - Fallback: first installed model named 'HomePage' that is a Page subclass
        """
        from wagtail.models import Page as WagtailPage

        if dotted:
            if "." not in dotted:
                raise ValueError("--homepage-model must be 'app_label.ModelName'")
            app_label, model_name = dotted.split(".", 1)
            return apps.get_model(app_label, model_name)

        # Prefer a 'home' app
        for app_config in apps.get_app_configs():
            # Fix: Check app_config.name for dotted paths, though label is usually simple.
            # safe check: (app_config.label == "home") or (app_config.name.endswith(".home"))
            if app_config.label == "home" or app_config.name.endswith(".home"):
                try:
                    return apps.get_model(app_config.label, "HomePage")
                except LookupError:
                    continue

        # Fallback: any installed HomePage model
        for model in apps.get_models():
            try:
                if model.__name__ == "HomePage" and issubclass(model, WagtailPage):
                    return model
            except TypeError:
                continue

        return None

    def _resolve_legal_page_model(self) -> Any:
        """
        Resolve LegalPage if available, otherwise fall back to StandardPage.
        """
        from wagtail.models import Page as WagtailPage

        for model in apps.get_models():
            try:
                if model.__name__ == "LegalPage" and issubclass(model, WagtailPage):
                    return model
            except TypeError:
                continue

        return StandardPage

    def _get_or_create_default_site(
        self, hostname: str | None, port: int | None, root: Page
    ) -> Site:
        Site.clear_site_root_paths_cache()

        site = Site.objects.filter(is_default_site=True).first()
        if site is None:
            site = Site.objects.create(
                hostname=hostname or "localhost",
                port=port or 8000,
                root_page=root,
                is_default_site=True,
                site_name="Showroom",
            )
        else:
            changed = False
            if hostname and site.hostname != hostname:
                site.hostname = hostname
                changed = True
            if port and site.port != port:
                site.port = port
                changed = True
            if not site.is_default_site:
                site.is_default_site = True
                changed = True
            if changed:
                site.save()

        Site.clear_site_root_paths_cache()
        return site

    def _clear_showroom(
        self, *, site: Site, slugs: _ShowroomSlugs, home_page_model: Any
    ) -> None:
        """
        Remove previously seeded pages safely.
        Only deletes content if we can find the seeded HomePage by its specific slug.
        """
        self.stdout.write("Clearing existing showroom pages...")

        # Locate the seeded home page
        home = home_page_model.objects.filter(slug=slugs.home).first()
        if not home:
            self.stdout.write(
                self.style.WARNING(
                    f"No existing showroom home with slug '{slugs.home}' found. "
                    "Skipping deletion to prevent data loss."
                )
            )
            return

        known_child_slugs = {
            slugs.showroom,
            slugs.contact,
            slugs.services,
            slugs.kitchen_sink,
            slugs.terms,
            slugs.privacy,
            slugs.cookies,
        }
        service_child_slugs = {slugs.service_one, slugs.service_two}

        for child in home.get_children().filter(slug__in=known_child_slugs):
            if child.slug == slugs.services:
                for service in child.get_children().filter(
                    slug__in=service_child_slugs
                ):
                    service.specific.delete()
            child.specific.delete()

        Site.clear_site_root_paths_cache()

    # -----------------------------------------------------------------------------
    # Page creation helpers
    # -----------------------------------------------------------------------------

    def _get_or_create_homepage(
        self, *, site: Site, root: Page, home_page_model: Any, slugs: _ShowroomSlugs
    ) -> Any:
        # Strict retrieval by slug - do not grab unrelated homepages
        home = home_page_model.objects.filter(slug=slugs.home).first()
        if not home:
            home = home_page_model(
                title="Theme Showroom", slug=slugs.home, intro="", body=None
            )
            root.add_child(instance=home)
            home.save_revision().publish()

        # Point default site root at the HomePage (homepage URL becomes "/")
        if site.root_page_id != home.id:
            site.root_page = home
            site.site_name = site.site_name or "Showroom"
            site.save()
            Site.clear_site_root_paths_cache()
        return home

    def _get_or_create_standard_page(
        self, *, parent: Page, title: str, slug: str
    ) -> StandardPage:
        existing = parent.get_children().type(StandardPage).filter(slug=slug).first()
        if existing:
            return existing.specific

        page = StandardPage(title=title, slug=slug, body=None)
        parent.add_child(instance=page)
        return page

    def _get_or_create_legal_page(
        self, *, parent: Page, title: str, slug: str, page_model: Any
    ) -> Page:
        existing = parent.get_children().type(page_model).filter(slug=slug).first()
        if existing:
            return existing.specific

        page = page_model(title=title, slug=slug)
        if hasattr(page, "body"):
            page.body = None
        parent.add_child(instance=page)
        return page

    def _get_or_create_services_index(
        self, *, parent: Page, title: str, slug: str
    ) -> ServiceIndexPage:
        existing = (
            parent.get_children().type(ServiceIndexPage).filter(slug=slug).first()
        )
        if existing:
            return existing.specific

        page = ServiceIndexPage(title=title, slug=slug, intro=None)
        parent.add_child(instance=page)
        return page

    def _get_or_create_service_page(
        self,
        *,
        parent: ServiceIndexPage,
        title: str,
        slug: str,
        short_description: str,
    ) -> ServicePage:
        existing = parent.get_children().type(ServicePage).filter(slug=slug).first()
        if existing:
            svc = existing.specific
            svc.short_description = short_description
            svc.save()
            return svc

        page = ServicePage(
            title=title,
            slug=slug,
            short_description=short_description,
            featured_image=None,
            body=None,
        )
        parent.add_child(instance=page)
        return page

    # -----------------------------------------------------------------------------
    # Images
    # -----------------------------------------------------------------------------

    @dataclass(frozen=True)
    class _Images:
        hero_id: int
        legacy_hero_id: int
        comparison_before_id: int
        comparison_after_id: int
        gallery_one_id: int
        gallery_two_id: int
        gallery_three_id: int
        portfolio_one_id: int
        portfolio_two_id: int
        trust_logo_one_id: int
        trust_logo_two_id: int
        image_block_id: int
        service_featured_one_id: int
        service_featured_two_id: int
        brand_logo_id: int
        favicon_id: int

    def _get_or_create_showroom_images(self) -> _Images:
        # Seed into specific collection
        collection = self._get_or_create_collection("Showroom")

        hero = self._get_or_create_image(
            "Showroom Hero", (1400, 900), "#0ea5e9", collection
        )
        legacy_hero = self._get_or_create_image(
            "Legacy Hero", (1200, 800), "#14b8a6", collection
        )
        before = self._get_or_create_image(
            "Comparison Before", (1400, 900), "#334155", collection
        )
        after = self._get_or_create_image(
            "Comparison After", (1400, 900), "#f97316", collection
        )
        g1 = self._get_or_create_image("Gallery 1", (1200, 800), "#a855f7", collection)
        g2 = self._get_or_create_image("Gallery 2", (1200, 800), "#22c55e", collection)
        g3 = self._get_or_create_image("Gallery 3", (1200, 800), "#eab308", collection)
        p1 = self._get_or_create_image(
            "Portfolio 1", (1200, 900), "#0f172a", collection
        )
        p2 = self._get_or_create_image(
            "Portfolio 2", (1200, 900), "#1f2937", collection
        )
        l1 = self._get_or_create_image(
            "Trust Logo 1", (600, 360), "#111827", collection
        )
        l2 = self._get_or_create_image(
            "Trust Logo 2", (600, 360), "#0b1220", collection
        )
        ib = self._get_or_create_image(
            "Content Image", (1600, 900), "#64748b", collection
        )
        sf1 = self._get_or_create_image(
            "Service Featured 1", (1600, 900), "#2563eb", collection
        )
        sf2 = self._get_or_create_image(
            "Service Featured 2", (1600, 900), "#dc2626", collection
        )
        brand = self._get_or_create_image(
            "Brand Logo", (800, 400), "#0f172a", collection
        )
        favicon = self._get_or_create_image(
            "Favicon", (256, 256), "#0f172a", collection
        )

        return self._Images(
            hero_id=hero.id,
            legacy_hero_id=legacy_hero.id,
            comparison_before_id=before.id,
            comparison_after_id=after.id,
            gallery_one_id=g1.id,
            gallery_two_id=g2.id,
            gallery_three_id=g3.id,
            portfolio_one_id=p1.id,
            portfolio_two_id=p2.id,
            trust_logo_one_id=l1.id,
            trust_logo_two_id=l2.id,
            image_block_id=ib.id,
            service_featured_one_id=sf1.id,
            service_featured_two_id=sf2.id,
            brand_logo_id=brand.id,
            favicon_id=favicon.id,
        )

    def _get_or_create_collection(self, name: str) -> Any:
        from wagtail.models import Collection

        root = Collection.get_first_root_node()
        existing = root.get_children().filter(name=name).first()
        if existing:
            return existing
        return root.add_child(name=name)

    def _get_or_create_image(
        self, title: str, size: tuple[int, int], color_hex: str, collection: Any
    ) -> Any:
        from wagtail.images import get_image_model

        image_model = get_image_model()
        existing = image_model.objects.filter(title=title).first()
        if existing:
            return existing

        if PILImage is None:  # pragma: no cover
            raise RuntimeError(
                "Pillow is required to generate placeholder images. "
                "Install it (it is usually included with Wagtail)."
            )

        rgb = self._hex_to_rgb(color_hex)
        img = PILImage.new("RGB", size, rgb)
        buf = BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)

        safe = self._slugify(title)
        filename = f"showroom-{safe}.png"

        return image_model.objects.create(
            title=title,
            file=ContentFile(buf.read(), name=filename),
            collection=collection,
        )

    def _hex_to_rgb(self, value: str) -> tuple[int, int, int]:
        v = value.strip().lstrip("#")
        if len(v) != 6:
            return (127, 127, 127)
        return (int(v[0:2], 16), int(v[2:4], 16), int(v[4:6], 16))

    # -----------------------------------------------------------------------------
    # Stream builders (PageStreamBlock)
    # -----------------------------------------------------------------------------

    def _build_starter_home_stream(
        self, *, images: _Images, contact_page: StandardPage
    ) -> Any:
        stream_block = PageStreamBlock()
        return stream_block.to_python(
            [
                {
                    "type": "hero_image",
                    "value": {
                        "headline": "<p>Build with <em>confidence</em></p>",
                        "subheadline": "Starter content to help you validate layouts and branding quickly.",
                        "ctas": [
                            {
                                "label": "Get in touch",
                                "url": "/contact/",
                                "style": "primary",
                                "open_in_new_tab": False,
                            },
                            {
                                "label": "Browse services",
                                "url": "/services/",
                                "style": "secondary",
                                "open_in_new_tab": False,
                            },
                        ],
                        "status": "Starter",
                        "image": images.hero_id,
                        "image_alt": "Starter hero placeholder image",
                        "overlay_opacity": "light",
                        "layout": "full",
                        "floating_card_label": "Local response time",
                        "floating_card_value": "< 1 day",
                    },
                },
                {
                    "type": "content",
                    "value": {
                        "align": "left",
                        "body": "<h2>Crafted for your next project</h2>"
                        "<p>Use this section to introduce your brand and explain the next steps.</p>"
                        "<ul><li>Highlight core services.</li>"
                        "<li>Explain your process.</li>"
                        "<li>Invite visitors to book a quote.</li></ul>",
                    },
                },
                {
                    "type": "testimonials",
                    "value": {
                        "eyebrow": "Testimonials",
                        "heading": "<p>What clients <em>say</em></p>",
                        "testimonials": [
                            {
                                "quote": "The team kept everything on schedule and the finish is perfect.",
                                "author_name": "Jordan Lee",
                                "company": "Lee Renovations",
                                "photo": None,
                                "rating": 5,
                            },
                            {
                                "quote": "Clear communication from start to finish.",
                                "author_name": "Morgan Cruz",
                                "company": "Cruz Design",
                                "photo": None,
                                "rating": 5,
                            },
                        ],
                    },
                },
            ]
        )

    def _build_home_stream(self, *, images: _Images, contact_page: StandardPage) -> Any:
        stream_block = PageStreamBlock()
        return stream_block.to_python(
            [
                {
                    "type": "hero_image",
                    "value": {
                        "headline": "<p>Theme <em>Showroom</em></p>",
                        "subheadline": "A seeded site tree with every block, ready for theme development.",
                        "ctas": [
                            {
                                "label": "View the showroom",
                                "url": "/showroom/",
                                "style": "primary",
                                "open_in_new_tab": False,
                            },
                            {
                                "label": "Contact",
                                # NOTE: Use stable paths rather than page.url because this block uses URLBlock.
                                # page.url may be None for unpublished pages during seeding.
                                "url": "/contact/",
                                "style": "secondary",
                                "open_in_new_tab": False,
                            },
                        ],
                        "status": "SUM Platform",
                        "image": images.hero_id,
                        "image_alt": "A placeholder hero image for theme showcase",
                        "overlay_opacity": "medium",
                        "layout": "full",
                        "floating_card_label": "Avg. response time",
                        "floating_card_value": "< 2 hrs",
                    },
                },
                {
                    "type": "trust_strip_logos",
                    "value": {
                        "eyebrow": "Trusted by",
                        "items": [
                            {
                                "logo": images.trust_logo_one_id,
                                "alt_text": "Trust badge one",
                                "url": "https://example.com/",
                            },
                            {
                                "logo": images.trust_logo_two_id,
                                "alt_text": "Trust badge two",
                                "url": "https://example.com/",
                            },
                        ],
                    },
                },
                {
                    "type": "service_cards",
                    "value": {
                        "eyebrow": "Services",
                        "heading": "<p>Browse our <em>services</em></p>",
                        "intro": "Use this section to test card layouts, hover states, and responsive grids.",
                        "view_all_link": "/services/",
                        "view_all_label": "View all services",
                        "layout_style": "default",
                        "cards": [
                            {
                                "icon": "☀️",
                                "image": None,
                                "title": "Solar Installation",
                                "description": "<p>Modern solar installs with clean finishing.</p>",
                                "link_url": "/services/solar-installation/",
                                "link_label": "Learn more",
                            },
                            {
                                "icon": "🏠",
                                "image": None,
                                "title": "Roofing",
                                "description": "<p>Durable roofing, designed for UK weather.</p>",
                                "link_url": "/services/roofing/",
                                "link_label": "Learn more",
                            },
                            {
                                "icon": "🔋",
                                "image": None,
                                "title": "Battery Storage",
                                "description": "<p>Store energy and improve self-consumption.</p>",
                                "link_url": "/showroom/",
                                "link_label": "See demo",
                            },
                        ],
                    },
                },
                {
                    "type": "testimonials",
                    "value": {
                        "eyebrow": "Client stories",
                        "heading": "<p>People <em>love</em> this</p>",
                        "testimonials": [
                            {
                                "quote": "Everything looked great across mobile and desktop — perfect for our brand.",
                                "author_name": "Alex Taylor",
                                "company": "Taylor & Sons",
                                "photo": None,
                                "rating": 5,
                            },
                            {
                                "quote": "The design tokens made it easy to adjust colours and typography site-wide.",
                                "author_name": "Sam Patel",
                                "company": "Patel Renovations",
                                "photo": None,
                                "rating": 5,
                            },
                            {
                                "quote": "Fast, clean, and consistent. Exactly what we need for client rollouts.",
                                "author_name": "Jamie Kim",
                                "company": "Kim Home Improvements",
                                "photo": None,
                                "rating": 5,
                            },
                        ],
                    },
                },
                {
                    "type": "gallery",
                    "value": {
                        "eyebrow": "Gallery",
                        "heading": "<p>Theme <em>imagery</em></p>",
                        "intro": "Use this gallery to check image ratios, captions, and grid behaviour.",
                        "images": [
                            {
                                "image": images.gallery_one_id,
                                "alt_text": "Gallery image one",
                                "caption": "Clean layout",
                            },
                            {
                                "image": images.gallery_two_id,
                                "alt_text": "Gallery image two",
                                "caption": "Responsive grid",
                            },
                            {
                                "image": images.gallery_three_id,
                                "alt_text": "Gallery image three",
                                "caption": "Typography scale",
                            },
                        ],
                    },
                },
                {
                    "type": "stats",
                    "value": {
                        "eyebrow": "By the numbers",
                        "intro": "Stats are a great place to validate spacing, type rhythm, and colour contrast.",
                        "items": [
                            {
                                "prefix": "",
                                "value": "500",
                                "suffix": "+",
                                "label": "Projects",
                            },
                            {
                                "prefix": "",
                                "value": "15",
                                "suffix": "yrs",
                                "label": "Experience",
                            },
                            {
                                "prefix": "",
                                "value": "98",
                                "suffix": "%",
                                "label": "Satisfaction",
                            },
                        ],
                    },
                },
            ]
        )

    def _build_showroom_stream(
        self,
        *,
        images: _Images,
        services_index: ServiceIndexPage,
        service_one: ServicePage,
        contact_page: StandardPage,
    ) -> Any:
        stream_block = PageStreamBlock()
        return stream_block.to_python(
            [
                {
                    "type": "hero_gradient",
                    "value": {
                        "headline": "<p>Block <em>Showroom</em></p>",
                        "subheadline": "A curated tour: every block type, spread across pages.",
                        "ctas": [
                            {
                                "label": "Services",
                                "url": "/services/",
                                "style": "primary",
                                "open_in_new_tab": False,
                            }
                        ],
                        "status": "Theme QA",
                        "gradient_style": "primary",
                    },
                },
                {
                    "type": "features",
                    "value": {
                        "heading": "Features",
                        "intro": "Check icons, alignment, and spacing across viewports.",
                        "features": [
                            {
                                "icon": "⚡",
                                "title": "Fast",
                                "description": "Token-driven styling and reusable patterns.",
                            },
                            {
                                "icon": "🧱",
                                "title": "Composable",
                                "description": "StreamField blocks let editors build pages without dev.",
                            },
                            {
                                "icon": "🔍",
                                "title": "SEO-ready",
                                "description": "Sitemap, robots.txt, meta tags, and schema helpers.",
                            },
                        ],
                    },
                },
                {
                    "type": "comparison",
                    "value": {
                        "accent_text": "Before / After",
                        "title": "Comparison slider",
                        "description": "Validate handle styling, overlays, and image cropping.",
                        "image_before": images.comparison_before_id,
                        "image_after": images.comparison_after_id,
                    },
                },
                {
                    "type": "manifesto",
                    "value": {
                        "eyebrow": "Manifesto",
                        "heading": "<p>Build with <em>consistency</em></p>",
                        "body": "<p>This section helps validate prose styling, link colours, and list rendering.</p>"
                        "<ul><li>Token-first</li><li>Accessible defaults</li><li>Theme override friendly</li></ul>",
                        "quote": "Good design is what you don’t notice — it just works.",
                        "cta_label": "See services",
                        "cta_url": "/services/",
                    },
                },
                {
                    "type": "portfolio",
                    "value": {
                        "eyebrow": "Portfolio",
                        "heading": "<p>Featured <em>work</em></p>",
                        "intro": "Check alternating layout offsets and typography scale.",
                        "view_all_label": "View all",
                        "view_all_link": "/",
                        "items": [
                            {
                                "image": images.portfolio_one_id,
                                "alt_text": "Portfolio project one",
                                "title": "Solar + battery upgrade",
                                "category": "Residential",
                                "location": "Kensington, London",
                                "services": "Solar • Battery",
                                "constraint": "Tight access",
                                "material": "Slate roof",
                                "outcome": "Lower bills",
                                "link_url": "/services/solar-installation/",
                            },
                            {
                                "image": images.portfolio_two_id,
                                "alt_text": "Portfolio project two",
                                "title": "Full roof replacement",
                                "category": "Commercial",
                                "location": "Richmond, London",
                                "services": "Roofing",
                                "constraint": "Winter schedule",
                                "material": "Clay tiles",
                                "outcome": "Weatherproof",
                                "link_url": "/services/",
                            },
                        ],
                    },
                },
                {
                    "type": "trust_strip",
                    "value": {
                        "items": [
                            {"text": "Fully insured"},
                            {"text": "5★ reviews"},
                            {"text": "Local team"},
                            {"text": "Transparent pricing"},
                        ]
                    },
                },
                {
                    "type": "editorial_header",
                    "value": {
                        "align": "center",
                        "eyebrow": "Editorial",
                        "heading": "<p>Content <em>blocks</em></p>",
                    },
                },
                {
                    "type": "content",
                    "value": {
                        "align": "left",
                        "body": "<h2>Rich text content</h2><p>This is a general-purpose content block.</p>"
                        "<p>Use it to validate headings, lists, links, and spacing.</p>",
                    },
                },
                {
                    "type": "table_of_contents",
                    "value": {
                        "items": [
                            {"label": "Scope of Works", "anchor": "scope-of-works"},
                            {"label": "Payments", "anchor": "payments"},
                            {"label": "Warranty", "anchor": "warranty"},
                        ]
                    },
                },
                {
                    "type": "legal_section",
                    "value": {
                        "anchor": "scope-of-works",
                        "heading": "Scope of Works",
                        "body": "<p>Legal sections ensure anchors and typography render correctly.</p>"
                        "<ul><li>Use clear subheadings.</li><li>Keep lists readable.</li></ul>",
                    },
                },
                {
                    "type": "legal_section",
                    "value": {
                        "anchor": "payments",
                        "heading": "Payments",
                        "body": "<p>Payment terms render as rich text.</p>"
                        "<p><strong>Pro tip:</strong> keep anchor IDs stable to avoid broken links.</p>",
                    },
                },
                {
                    "type": "legal_section",
                    "value": {
                        "anchor": "warranty",
                        "heading": "Warranty",
                        "body": "<p>Warranty language can mix paragraphs and lists.</p>"
                        "<ul><li>Outline coverage.</li><li>Clarify exclusions.</li></ul>",
                    },
                },
                {
                    "type": "quote",
                    "value": {
                        "quote": "Design systems are what keep themes consistent as they scale.",
                        "author": "SUM Platform",
                        "role": "Core team",
                    },
                },
                {
                    "type": "image_block",
                    "value": {
                        "image": images.image_block_id,
                        "alt_text": "A cinematic placeholder image",
                        "caption": "Full-bleed image block with caption.",
                        "full_width": False,
                    },
                },
                {
                    "type": "buttons",
                    "value": {
                        "alignment": "left",
                        "buttons": [
                            {"label": "Generic Button", "style": "primary", "url": "/"},
                            {
                                "label": "Secondary Style",
                                "style": "secondary",
                                "url": "/",
                            },
                        ],
                    },
                },
            ]
        )

    def _build_kitchen_sink_stream(
        self,
        *,
        images: _Images,
        services_index: ServiceIndexPage,
        service_one: ServicePage,
        contact_page: StandardPage,
    ) -> Any:
        """
        Combine all block types into a single page stream for rapid testing.
        """
        stream_block = PageStreamBlock()

        # Combine home stream + showroom stream blocks to cover everything
        home_data = self._build_home_stream(images=images, contact_page=contact_page)
        showroom_data = self._build_showroom_stream(
            images=images,
            services_index=services_index,
            service_one=service_one,
            contact_page=contact_page,
        )

        # NOTE:
        # home_data/showroom_data are StreamValues (iterating yields StreamChild objects).
        # StreamBlock.to_python expects *raw* stream data (list of dicts/tuples), so we
        # convert back to raw and only to_python() once.
        home_raw = (
            home_data.get_prep_value()
            if hasattr(home_data, "get_prep_value")
            else home_data
        )
        showroom_raw = (
            showroom_data.get_prep_value()
            if hasattr(showroom_data, "get_prep_value")
            else showroom_data
        )

        combined_raw = list(home_raw) + list(showroom_raw)
        return stream_block.to_python(combined_raw)

    def _build_services_index_intro_stream(self, *, images: _Images) -> Any:
        stream_block = PageStreamBlock()
        return stream_block.to_python(
            [
                {
                    "type": "hero_gradient",
                    "value": {
                        "headline": "<p>Our <em>Services</em></p>",
                        "subheadline": "Professional trades for every requirement.",
                        "ctas": [],
                        "status": "Available",
                        "gradient_style": "secondary",
                    },
                },
            ]
        )

    def _build_service_page_stream(
        self, *, images: _Images, page: ServicePage, contact_page: StandardPage
    ) -> Any:
        stream_block = PageStreamBlock()
        return stream_block.to_python(
            [
                {
                    "type": "content",
                    "value": {
                        "align": "left",
                        "body": f"<p>Detail content for {page.title}.</p>"
                        "<h3>Why choose us?</h3>"
                        "<ul><li>Experienced team</li><li>Guaranteed work</li><li>Fast turnaround</li></ul>",
                    },
                },
                {
                    "type": "cta_banner",
                    "value": {
                        "heading": "Ready to start?",
                        "description": "Get a free quote today.",
                        "cta_label": "Contact us",
                        "cta_url": "/contact/",  # or contact_page.url if available
                    },
                },
            ]
        )

    def _build_contact_stream(self, *, images: _Images) -> Any:
        stream_block = PageStreamBlock()
        return stream_block.to_python(
            [
                {
                    "type": "hero_gradient",
                    "value": {
                        "headline": "<p>Get in <em>touch</em></p>",
                        "subheadline": "We’d love to hear from you.",
                        "ctas": [],
                        "status": "Open",
                        "gradient_style": "default",
                    },
                },
                # Note: 'form' block would go here if we had a FormPage or embedded form block.
                # For now using content placeholder.
                {
                    "type": "content",
                    "value": {
                        "align": "center",
                        "body": "<p>Phone: 020 1234 5678<br>Email: hello@example.com</p>",
                    },
                },
            ]
        )

    def _build_terms_sections(self) -> tuple[str, list[dict[str, str]]]:
        intro = "Ground rules for using this starter site and reviewing layouts."
        sections = [
            {
                "anchor": "scope-of-works",
                "heading": "Scope of Works",
                "body": "<p>This starter content is for layout preview only.</p>"
                "<ul><li>Keep experiments to non-sensitive data.</li>"
                "<li>Use it to validate typography and spacing.</li></ul>",
            },
            {
                "anchor": "payments",
                "heading": "Payments",
                "body": "<p>Payment terms render as rich text with lists and links.</p>"
                "<p>Update this copy with client-approved wording before launch.</p>",
            },
            {
                "anchor": "warranty",
                "heading": "Warranty",
                "body": "<p>Replace this placeholder with your project-specific warranty details.</p>",
            },
        ]
        return intro, sections

    def _build_terms_stream(self) -> Any:
        intro, sections = self._build_terms_sections()
        return self._build_legal_stream(
            heading="Terms & Conditions",
            intro=intro,
            sections=sections,
        )

    def _build_privacy_sections(self) -> tuple[str, list[dict[str, str]]]:
        intro = (
            "How this starter site handles demo requests and placeholder contact data."
        )
        sections = [
            {
                "anchor": "data-collection",
                "heading": "Data we collect",
                "body": "<p>Contact details submitted through demo forms.</p>"
                "<p>Anonymous analytics used to validate reporting flows.</p>",
            },
            {
                "anchor": "data-usage",
                "heading": "How we use it",
                "body": "<p>Submissions route to the default email in Branding settings.</p>"
                "<p>Analytics data powers reporting dashboards only.</p>",
            },
            {
                "anchor": "your-choices",
                "heading": "Your choices",
                "body": "<p>Clear seeded data anytime by rerunning the command or editing in Wagtail.</p>",
            },
        ]
        return intro, sections

    def _build_privacy_stream(self) -> Any:
        intro, sections = self._build_privacy_sections()
        return self._build_legal_stream(
            heading="Privacy Notice",
            intro=intro,
            sections=sections,
        )

    def _build_cookie_sections(self) -> tuple[str, list[dict[str, str]]]:
        intro = "Details on cookie usage and consent controls for this starter site."
        sections = [
            {
                "anchor": "cookies-we-use",
                "heading": "Cookies we use",
                "body": "<p>Consent and analytics cookies are used to support the demo site.</p>"
                "<ul><li>Consent status</li><li>Analytics identifiers</li></ul>",
            },
            {
                "anchor": "consent-controls",
                "heading": "Consent controls",
                "body": "<p>Use the Manage cookies link in the footer to update your preferences.</p>",
            },
            {
                "anchor": "updates",
                "heading": "Updates",
                "body": "<p>Cookie settings may change as policies are updated.</p>",
            },
        ]
        return intro, sections

    def _build_cookie_stream(self) -> Any:
        intro, sections = self._build_cookie_sections()
        return self._build_legal_stream(
            heading="Cookie Policy",
            intro=intro,
            sections=sections,
        )

    def _build_legal_stream(
        self, *, heading: str, intro: str, sections: list[dict[str, str]]
    ) -> Any:
        stream_block = PageStreamBlock()
        toc_items = [
            {"label": section["heading"], "anchor": section["anchor"]}
            for section in sections
        ]
        stream: list[dict[str, Any]] = [
            {
                "type": "editorial_header",
                "value": {
                    "align": "center",
                    "eyebrow": "Legal",
                    "heading": f"<p>{heading}</p>",
                },
            },
            {
                "type": "content",
                "value": {
                    "align": "left",
                    "body": f"<p>{intro}</p>",
                },
            },
        ]
        if toc_items:
            stream.append({"type": "table_of_contents", "value": {"items": toc_items}})
        for section in sections:
            stream.append(
                {
                    "type": "legal_section",
                    "value": {
                        "anchor": section["anchor"],
                        "heading": section["heading"],
                        "body": section["body"],
                    },
                }
            )
        return stream_block.to_python(stream)

    def _build_legal_sections(
        self, sections: list[dict[str, str]]
    ) -> list[tuple[str, dict[str, str]]]:
        return [
            (
                "section",
                {
                    "anchor": section["anchor"],
                    "heading": section["heading"],
                    "body": section["body"],
                },
            )
            for section in sections
        ]

    def _apply_legal_page_content(
        self,
        page: Page,
        *,
        heading: str,
        intro: str,
        sections: list[dict[str, str]],
    ) -> None:
        """
        Apply legal content to a page, supporting both LegalPage (sections field)
        and StandardPage (body StreamField) models.

        Args:
            page: The page instance to populate (LegalPage or StandardPage).
            heading: The main heading for the legal content.
            intro: Introductory text/description.
            sections: List of dicts with 'anchor', 'title', and 'content' keys.
        """
        if hasattr(page, "sections"):
            page.sections = self._build_legal_sections(sections)
            page.search_description = intro
        else:
            page.body = self._build_legal_stream(
                heading=heading,
                intro=intro,
                sections=sections,
            )
        page.save_revision().publish()

    # -----------------------------------------------------------------------------
    # Branding & Navigation
    # -----------------------------------------------------------------------------

    def _seed_branding(
        self, *, site: Site, images: _Images, terms: Page, privacy: Page, cookies: Page
    ) -> None:
        settings = SiteSettings.for_site(site)
        # SiteSettings lives in sum_core and uses explicit fields.
        settings.company_name = "Showroom"
        settings.header_logo_id = images.brand_logo_id
        settings.footer_logo_id = images.brand_logo_id
        settings.favicon_id = images.favicon_id
        settings.email = "hello@example.com"
        settings.phone_number = "0800 123 4567"
        settings.facebook_url = "https://facebook.com"
        settings.instagram_url = "https://instagram.com"
        settings.cookie_banner_enabled = True
        settings.cookie_consent_version = "2024-01"
        settings.terms_page = terms
        settings.privacy_policy_page = privacy
        settings.cookie_policy_page = cookies
        settings.save()

    def _seed_navigation(
        self,
        *,
        site: Site,
        home: Page,
        contact: Page,
        services_index: Page,
        service_one: Page,
        service_two: Page,
        terms: Page,
        privacy: Page,
        cookies: Page,
        showroom: Page | None,
        kitchen_sink: Page | None,
    ) -> None:
        # HeaderNavigation / FooterNavigation are StreamField-based settings.
        header = HeaderNavigation.for_site(site)

        menu_items = [
            {
                "type": "item",
                "value": {
                    "label": "Home",
                    "link": {
                        "link_type": "page",
                        "page": home.id,
                        "link_text": "Home",
                        "open_in_new_tab": False,
                    },
                    "children": [],
                },
            },
            {
                "type": "item",
                "value": {
                    "label": "Services",
                    "link": {
                        "link_type": "page",
                        "page": services_index.id,
                        "link_text": "Services",
                        "open_in_new_tab": False,
                    },
                    "children": [
                        {
                            "label": service_one.title,
                            "link": {
                                "link_type": "page",
                                "page": service_one.id,
                                "link_text": service_one.title,
                                "open_in_new_tab": False,
                            },
                            "children": [],
                        },
                        {
                            "label": service_two.title,
                            "link": {
                                "link_type": "page",
                                "page": service_two.id,
                                "link_text": service_two.title,
                                "open_in_new_tab": False,
                            },
                            "children": [],
                        },
                    ],
                },
            },
        ]
        if showroom is not None:
            menu_items.append(
                {
                    "type": "item",
                    "value": {
                        "label": "Showroom",
                        "link": {
                            "link_type": "page",
                            "page": showroom.id,
                            "link_text": "Showroom",
                            "open_in_new_tab": False,
                        },
                        "children": [],
                    },
                }
            )
        menu_items.append(
            {
                "type": "item",
                "value": {
                    "label": "Contact",
                    "link": {
                        "link_type": "page",
                        "page": contact.id,
                        "link_text": "Contact",
                        "open_in_new_tab": False,
                    },
                    "children": [],
                },
            }
        )
        header.menu_items = menu_items

        header.header_cta_enabled = True
        header.header_cta_text = "Contact"
        header.header_cta_link = [
            {
                "type": "link",
                "value": {
                    "link_type": "page",
                    "page": contact.id,
                    "link_text": "Contact",
                    "open_in_new_tab": False,
                },
            }
        ]

        header.mobile_cta_enabled = True
        header.mobile_cta_button_enabled = True
        header.mobile_cta_button_text = "Contact"
        header.mobile_cta_button_link = [
            {
                "type": "link",
                "value": {
                    "link_type": "page",
                    "page": contact.id,
                    "link_text": "Contact",
                    "open_in_new_tab": False,
                },
            }
        ]
        header.save()

        footer = FooterNavigation.for_site(site)

        explore_links = [
            {
                "link_type": "page",
                "page": home.id,
                "link_text": "Home",
                "open_in_new_tab": False,
            },
        ]
        if showroom is not None:
            explore_links.append(
                {
                    "link_type": "page",
                    "page": showroom.id,
                    "link_text": "Showroom",
                    "open_in_new_tab": False,
                }
            )
        if kitchen_sink is not None:
            explore_links.append(
                {
                    "link_type": "page",
                    "page": kitchen_sink.id,
                    "link_text": "Kitchen Sink",
                    "open_in_new_tab": False,
                }
            )

        footer.link_sections = [
            {
                "type": "section",
                "value": {
                    "title": "Explore",
                    "links": explore_links,
                },
            },
            {
                "type": "section",
                "value": {
                    "title": "Services",
                    "links": [
                        {
                            "link_type": "page",
                            "page": services_index.id,
                            "link_text": "All Services",
                            "open_in_new_tab": False,
                        },
                        {
                            "link_type": "page",
                            "page": service_one.id,
                            "link_text": service_one.title,
                            "open_in_new_tab": False,
                        },
                        {
                            "link_type": "page",
                            "page": service_two.id,
                            "link_text": service_two.title,
                            "open_in_new_tab": False,
                        },
                    ],
                },
            },
            {
                "type": "section",
                "value": {
                    "title": "Company",
                    "links": [
                        {
                            "link_type": "page",
                            "page": contact.id,
                            "link_text": "Contact",
                            "open_in_new_tab": False,
                        },
                    ],
                },
            },
            {
                "type": "section",
                "value": {
                    "title": "Legal",
                    "links": [
                        {
                            "link_type": "page",
                            "page": terms.id,
                            "link_text": "Terms",
                            "open_in_new_tab": False,
                        },
                        {
                            "link_type": "page",
                            "page": privacy.id,
                            "link_text": "Privacy",
                            "open_in_new_tab": False,
                        },
                        {
                            "link_type": "page",
                            "page": cookies.id,
                            "link_text": "Cookies",
                            "open_in_new_tab": False,
                        },
                    ],
                },
            },
        ]

        # Keep footer social links blank so templates can demonstrate the
        # effective-settings fallback to Branding SiteSettings.
        footer.social_facebook = ""
        footer.social_instagram = ""
        footer.save()

    def _slugify(self, text: str) -> str:
        # Simple slugify for filenames
        text = text.lower()
        return re.sub(r"[^a-z0-9]+", "-", text).strip("-")
