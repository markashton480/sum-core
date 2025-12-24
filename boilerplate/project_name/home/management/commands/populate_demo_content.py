"""
Name: Populate Demo Content Management Command
Path: project_name/home/management/commands/populate_demo_content.py
Purpose: Generates realistic dummy content for Wagtail pages to enable fast iteration during development.
         Creates HomePage and multiple StandardPages with varied StreamField blocks.
Family: Called by Django management command system (python manage.py populate_demo_content)
Dependencies:
    - wagtail.models (Page)
    - sum_core.pages.StandardPage
    - project_name.home.models.HomePage (dynamically imported)
    - Faker for realistic content generation
"""

from __future__ import annotations

import random
from typing import Any

from django.apps import apps
from django.core.management.base import BaseCommand, CommandParser
from wagtail.models import Page, Site

try:
    from faker import Faker
except ImportError:
    Faker = None


class Command(BaseCommand):
    """
    Management command to populate demo content for fast development iteration.

    Usage:
        python manage.py populate_demo_content
        python manage.py populate_demo_content --clear  # Remove existing demo pages first
    """

    help = "Populate demo content for Wagtail pages with realistic dummy data"

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.fake: Any = Faker() if Faker is not None else None

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Delete existing demo content before creating new content",
        )
        parser.add_argument(
            "--no-images",
            action="store_true",
            help="Skip creating image blocks (useful if no sample images available)",
        )

    def handle(self, *args: Any, **options: dict[str, Any]) -> None:
        if not self.fake:
            self.stdout.write(
                self.style.ERROR(
                    "Faker library not installed. Install with: pip install faker --break-system-packages"
                )
            )
            return

        self.no_images = options["no_images"]

        if options["clear"]:
            self.clear_demo_content()

        self.create_demo_content()

        self.stdout.write(self.style.SUCCESS("\n✓ Demo content created successfully!"))

    def get_models(self) -> tuple[Any, Any]:
        """Dynamically import models based on Django app registry."""
        # Find HomePage model using app label pattern
        home_page_model = None
        for app_config in apps.get_app_configs():
            if "home" in app_config.label:
                try:
                    home_page_model = apps.get_model(app_config.label, "HomePage")
                    break
                except LookupError:
                    continue

        if not home_page_model:
            self.stdout.write(
                self.style.ERROR(
                    "HomePage model not found. Make sure your home app is in INSTALLED_APPS"
                )
            )
            return None, None

        # Get StandardPage
        try:
            from sum_core import pages

            standard_page_model = pages.StandardPage
        except ImportError:
            self.stdout.write(self.style.ERROR("sum_core.pages not installed"))
            return None, None

        return home_page_model, standard_page_model

    def clear_demo_content(self) -> None:
        """Remove existing demo pages."""
        self.stdout.write("Clearing existing demo content...")

        home_page_model, standard_page_model = self.get_models()
        if not home_page_model or not standard_page_model:
            return

        # Delete StandardPages
        deleted_standard = standard_page_model.objects.all().delete()
        self.stdout.write(f"  Deleted {deleted_standard[0]} StandardPages")

        # Delete HomePages (but not the root page)
        deleted_home = home_page_model.objects.exclude(depth=2).delete()
        self.stdout.write(f"  Deleted {deleted_home[0]} HomePages")

    def create_demo_content(self) -> None:
        """Create demo pages with varied content."""
        home_page_model, standard_page_model = self.get_models()
        if not home_page_model or not standard_page_model:
            return

        # Get or create site root
        root_page = Page.objects.get(depth=1)

        # Check if HomePage already exists
        home_page = home_page_model.objects.first()
        if not home_page:
            self.stdout.write("Creating HomePage...")
            home_page = self._create_home_page(home_page_model, root_page)
        else:
            self.stdout.write(f"Using existing HomePage: {home_page.title}")

        # Create StandardPages with varied content
        self.stdout.write("\nCreating StandardPages...")

        pages_config = [
            ("About Us", self._build_about_page),
            ("Our Services", self._build_services_page),
            ("Portfolio", self._build_portfolio_page),
            ("FAQ", self._build_faq_page),
            ("Contact", self._build_contact_page),
            ("How It Works", self._build_process_page),
        ]

        for title, builder_func in pages_config:
            # Check if page already exists to avoid duplicates
            existing_page = (
                root_page.get_children().filter(slug=self._slugify(title)).first()
            )
            if existing_page:
                self.stdout.write(f"  ⊙ Skipping (already exists): {title}")
                continue

            page = standard_page_model(
                title=title,
                slug=self._slugify(title),
                body=builder_func(),
            )
            root_page.add_child(instance=page)
            page.save_revision().publish()
            self.stdout.write(f"  ✓ Created: {title}")

    def _create_home_page(self, home_page_model: Any, parent: Page) -> Page:
        """Create a HomePage with hero and feature content."""
        import uuid

        body_content = [
            self._build_hero_gradient(),
            self._build_stats_block(),
            self._build_service_cards(card_count=3),
            self._build_testimonials_block(count=3),
        ]

        # Create with temporary unique slug to avoid conflicts
        temp_slug = f"home-{uuid.uuid4().hex[:8]}"
        home_page = home_page_model(
            title="Home",
            slug=temp_slug,
            intro=f"<p>{self.fake.paragraph(nb_sentences=2)}</p>",
            body=body_content,
        )

        parent.add_child(instance=home_page)
        home_page.save_revision().publish()

        # Get the site and old root page
        site = Site.objects.first()
        old_root = None
        if site:
            old_root = site.root_page
            # Set new page as site root
            site.root_page = home_page
            site.save()

        # Delete the old default Wagtail page if it exists
        if old_root and old_root.id != parent.id:
            old_slug = old_root.slug
            old_title = old_root.title
            old_root.delete()
            self.stdout.write(f"  ✓ Removed old page: '{old_title}' (slug: {old_slug})")

        # Now update slug to 'home' since the old one is gone
        home_page.slug = "home"
        home_page.save()

        self.stdout.write("  ✓ Created HomePage")
        return home_page

    def _build_about_page(self) -> list[tuple[str, dict[str, Any]]]:
        """Build About page with editorial content."""
        return [
            self._build_hero_gradient(
                headline="About <em>Our Company</em>",
                subheadline="Building sustainable solutions since 2020",
            ),
            self._build_rich_text_content(paragraphs=3),
            self._build_stats_block(),
            self._build_rich_text_content(paragraphs=2, center=True),
            self._build_testimonials_block(count=2),
        ]

    def _build_services_page(self) -> list[tuple[str, dict[str, Any]]]:
        """Build Services page with service cards and features."""
        return [
            self._build_hero_gradient(
                headline="Our <em>Services</em>",
                subheadline="Comprehensive solutions tailored to your needs",
            ),
            self._build_service_cards(card_count=6),
            self._build_divider(),
            self._build_rich_text_content(paragraphs=2, center=True),
            self._build_testimonials_block(count=3),
        ]

    def _build_portfolio_page(self) -> list[tuple[str, dict[str, Any]]]:
        """Build Portfolio page with project showcase."""
        return [
            self._build_editorial_header(
                heading="Our <em>Portfolio</em>",
                eyebrow="Recent Work",
            ),
            self._build_rich_text_content(paragraphs=1, center=True),
            self._build_portfolio_block(item_count=4),
            self._build_spacer("large"),
            (
                "buttons",
                {
                    "alignment": "center",
                    "buttons": [
                        {
                            "label": "View All Projects",
                            "url": "/portfolio/",
                            "style": "primary",
                        }
                    ],
                },
            ),
        ]

    def _build_faq_page(self) -> list[tuple[str, dict[str, Any]]]:
        """Build FAQ page with questions and answers."""
        return [
            self._build_editorial_header(
                heading="Frequently Asked <em>Questions</em>",
                eyebrow="Help Centre",
            ),
            self._build_faq_block(),
            self._build_spacer("large"),
            self._build_rich_text_content(paragraphs=1, center=True),
            (
                "buttons",
                {
                    "alignment": "center",
                    "buttons": [
                        {
                            "label": "Contact Support",
                            "url": "/contact/",
                            "style": "primary",
                        }
                    ],
                },
            ),
        ]

    def _build_contact_page(self) -> list[tuple[str, dict[str, Any]]]:
        """Build Contact page with form."""
        return [
            self._build_editorial_header(
                heading="Get in <em>Touch</em>",
                eyebrow="Contact Us",
            ),
            self._build_rich_text_content(paragraphs=1, center=True),
            self._build_contact_form(),
        ]

    def _build_process_page(self) -> list[tuple[str, dict[str, Any]]]:
        """Build How It Works page with process steps."""
        return [
            self._build_hero_gradient(
                headline="How It <em>Works</em>",
                subheadline="Our proven process for delivering results",
            ),
            self._build_process_steps(),
            self._build_spacer("large"),
            self._build_testimonials_block(count=2),
            self._build_spacer("medium"),
            (
                "buttons",
                {
                    "alignment": "center",
                    "buttons": [
                        {
                            "label": "Get Started",
                            "url": "/contact/",
                            "style": "primary",
                        },
                        {
                            "label": "Learn More",
                            "url": "/services/",
                            "style": "secondary",
                        },
                    ],
                },
            ),
        ]

    # ========== Block Builders ==========

    def _build_hero_gradient(
        self,
        headline: str | None = None,
        subheadline: str | None = None,
    ) -> tuple[str, dict[str, Any]]:
        """Build a gradient hero block."""
        if not headline:
            company = self.fake.company()
            headline = f"Welcome to <em>{company}</em>"

        if not subheadline:
            subheadline = self.fake.catch_phrase()

        return (
            "hero_gradient",
            {
                "headline": f"<p>{headline}</p>",
                "subheadline": subheadline,
                "ctas": [
                    {
                        "label": "Get Started",
                        "url": "/contact/",
                        "style": "primary",
                        "open_in_new_tab": False,
                    },
                    {
                        "label": "Learn More",
                        "url": "/about/",
                        "style": "secondary",
                        "open_in_new_tab": False,
                    },
                ],
                "status": "",
                "gradient_style": random.choice(["primary", "secondary", "accent"]),
            },
        )

    def _build_service_cards(
        self,
        card_count: int = 3,
    ) -> tuple[str, dict[str, Any]]:
        """Build service cards block."""
        services = [
            ("🔧", "Installation", "Professional installation services"),
            ("⚡", "Maintenance", "Regular maintenance and support"),
            ("📊", "Consulting", "Expert consulting and strategy"),
            ("🎯", "Training", "Comprehensive training programs"),
            ("🔒", "Security", "Advanced security solutions"),
            ("🚀", "Optimization", "Performance optimization services"),
        ]

        cards = []
        for i in range(min(card_count, len(services))):
            icon, title, desc = services[i]
            cards.append(
                {
                    "icon": icon,
                    "image": None,
                    "title": title,
                    "description": f"<p>{desc}. {self.fake.sentence()}</p>",
                    "link_url": f"/services/{self._slugify(title)}/",
                    "link_label": "Learn more",
                }
            )

        return (
            "service_cards",
            {
                "eyebrow": "What We Offer",
                "heading": "<p>Our <em>Services</em></p>",
                "intro": self.fake.paragraph(nb_sentences=2),
                "cards": cards,
                "layout_style": "default",
            },
        )

    def _build_testimonials_block(
        self,
        count: int = 3,
    ) -> tuple[str, dict[str, Any]]:
        """Build testimonials block."""
        testimonials = []
        for _ in range(count):
            testimonials.append(
                {
                    "quote": self.fake.paragraph(nb_sentences=3),
                    "author_name": self.fake.name(),
                    "company": self.fake.company(),
                    "photo": None,
                    "rating": random.randint(4, 5),
                }
            )

        return (
            "testimonials",
            {
                "eyebrow": "Client Stories",
                "heading": "<p>What Our <em>Clients Say</em></p>",
                "testimonials": testimonials,
            },
        )

    def _build_stats_block(self) -> tuple[str, dict[str, Any]]:
        """Build statistics block."""
        return (
            "stats",
            {
                "eyebrow": "By the Numbers",
                "intro": self.fake.sentence(),
                "items": [
                    {
                        "value": "500",
                        "label": "Projects Completed",
                        "prefix": ">",
                        "suffix": "+",
                    },
                    {
                        "value": "15",
                        "label": "Years Experience",
                        "prefix": "",
                        "suffix": "yrs",
                    },
                    {
                        "value": "98",
                        "label": "Client Satisfaction",
                        "prefix": "",
                        "suffix": "%",
                    },
                    {
                        "value": "24",
                        "label": "Support Available",
                        "prefix": "",
                        "suffix": "/7",
                    },
                ],
            },
        )

    def _build_process_steps(self) -> tuple[str, dict[str, Any]]:
        """Build process steps block."""
        steps = [
            ("Initial Consultation", "We discuss your needs and objectives"),
            ("Planning & Design", "Our team creates a customized solution"),
            ("Implementation", "We execute the plan with precision"),
            ("Testing & QA", "Rigorous testing ensures quality"),
            ("Launch & Support", "Go live with ongoing support"),
        ]

        step_blocks = []
        for i, (title, desc) in enumerate(steps, 1):
            step_blocks.append(
                {
                    "number": i,
                    "title": title,
                    "description": f"<p>{desc}. {self.fake.sentence()}</p>",
                }
            )

        return (
            "process",
            {
                "eyebrow": "Our Approach",
                "heading": "<p>How We <em>Work</em></p>",
                "intro": f"<p>{self.fake.paragraph(nb_sentences=2)}</p>",
                "steps": step_blocks,
            },
        )

    def _build_faq_block(self) -> tuple[str, dict[str, Any]]:
        """Build FAQ accordion block."""
        faqs = [
            (
                "How do I get started?",
                "Getting started is easy! Simply contact us through our form or give us a call.",
            ),
            (
                "What are your pricing plans?",
                "We offer flexible pricing based on your specific needs. Contact us for a custom quote.",
            ),
            (
                "Do you offer support?",
                "Yes, we provide 24/7 support to all our clients with comprehensive assistance.",
            ),
            (
                "How long does implementation take?",
                "Timeline varies by project, but typical implementations take 2-4 weeks.",
            ),
            (
                "What makes you different?",
                "Our commitment to quality, customer service, and innovative solutions sets us apart.",
            ),
        ]

        faq_items = []
        for question, answer in faqs:
            faq_items.append(
                {
                    "question": question,
                    "answer": f"<p>{answer} {self.fake.sentence()}</p>",
                }
            )

        return (
            "faq",
            {
                "eyebrow": "Common Questions",
                "heading": "<p><em>FAQ</em></p>",
                "intro": f"<p>{self.fake.sentence()}</p>",
                "items": faq_items,
            },
        )

    def _build_portfolio_block(
        self,
        item_count: int = 4,
    ) -> tuple[str, dict[str, Any]]:
        """Build portfolio items block."""
        items = []
        locations = ["London", "Manchester", "Birmingham", "Leeds", "Bristol"]
        services = [
            "Installation • Maintenance",
            "Consulting • Training",
            "Design • Implementation",
        ]

        for i in range(item_count):
            items.append(
                {
                    "image": None,  # Would need actual images
                    "alt_text": f"Project {i+1}",
                    "title": self.fake.catch_phrase(),
                    "location": f"{self.fake.city()}, {random.choice(locations)}",
                    "services": random.choice(services),
                    "link_url": f"/portfolio/project-{i+1}/",
                }
            )

        return (
            "portfolio",
            {
                "eyebrow": "Recent Work",
                "heading": "<p>Featured <em>Projects</em></p>",
                "intro": self.fake.paragraph(nb_sentences=1),
                "items": items,
            },
        )

    def _build_contact_form(self) -> tuple[str, dict[str, Any]]:
        """Build contact form block."""
        return (
            "contact_form",
            {
                "eyebrow": "Get In Touch",
                "heading": "<p>Send us a <em>Message</em></p>",
                "intro": f"<p>{self.fake.paragraph(nb_sentences=2)}</p>",
                "success_message": "Thank you for your enquiry! We'll get back to you soon.",
                "submit_label": "Send Enquiry",
            },
        )

    def _build_rich_text_content(
        self,
        paragraphs: int = 2,
        center: bool = False,
    ) -> tuple[str, dict[str, Any]]:
        """Build rich text content block."""
        content = "".join(
            [f"<p>{self.fake.paragraph(nb_sentences=3)}</p>" for _ in range(paragraphs)]
        )

        return (
            "content",
            {
                "align": "center" if center else "left",
                "body": content,
            },
        )

    def _build_editorial_header(
        self,
        heading: str,
        eyebrow: str = "",
    ) -> tuple[str, dict[str, Any]]:
        """Build editorial header block."""
        return (
            "editorial_header",
            {
                "align": "center",
                "eyebrow": eyebrow,
                "heading": f"<p>{heading}</p>",
            },
        )

    def _build_spacer(self, size: str = "medium") -> tuple[str, dict[str, Any]]:
        """Build spacer block."""
        return ("spacer", {"size": size})

    def _build_divider(self, style: str = "muted") -> tuple[str, dict[str, Any]]:
        """Build divider block."""
        return ("divider", {"style": style})

    # ========== Helpers ==========

    def _slugify(self, text: str) -> str:
        """Convert text to URL-friendly slug."""
        import re

        text = text.lower()
        text = re.sub(r"[^\w\s-]", "", text)
        text = re.sub(r"[-\s]+", "-", text)
        return text.strip("-")
