"""
Name: Wagtail Trash Test Fixtures
Path: core/sum_core/wagtail_trash/tests/conftest.py
Purpose: Pytest fixtures for wagtail_trash tests.
Family: SUM Platform Core - Testing
"""

import pytest
from django.contrib.auth import get_user_model
from wagtail.models import Page, Site

User = get_user_model()


@pytest.fixture
def admin_user(db):
    """Create an admin user for testing."""
    return User.objects.create_superuser(
        username="admin",
        email="admin@test.com",
        password="password123",
    )


@pytest.fixture
def site_root(db):
    """Get or create the root page."""
    return Page.objects.get(depth=1)


@pytest.fixture
def default_site(db, site_root):
    """Get or create the default site with a home page."""
    # Get existing home page or create one
    try:
        home = Page.objects.get(depth=2, slug="home")
    except Page.DoesNotExist:
        home = Page(title="Home", slug="home")
        site_root.add_child(instance=home)
        home.refresh_from_db()

    # Get or create default site, ensuring root_page is our home page
    site = Site.objects.filter(is_default_site=True).first()
    if not site:
        site = Site.objects.create(
            hostname="localhost",
            root_page=home,
            is_default_site=True,
            site_name="Test Site",
        )
    elif site.root_page_id != home.pk:
        # Update existing site to use our home page
        site.root_page = home
        site.save()

    return site


@pytest.fixture
def site_with_pages(db, default_site):
    """
    Create a site with a multi-level page tree for testing.

    Structure:
        Home (site root, depth 2)
        ├── About (depth 3)
        ├── Blog (depth 3)
        │   ├── Post 1 (depth 4)
        │   └── Post 2 (depth 4)
        └── Contact (depth 3)
    """
    home = default_site.root_page
    home.refresh_from_db()

    # Create child pages (these will be at depth 3)
    about = Page(title="About", slug="about")
    home.add_child(instance=about)
    about.refresh_from_db()

    blog = Page(title="Blog", slug="blog")
    home.add_child(instance=blog)
    blog.refresh_from_db()

    contact = Page(title="Contact", slug="contact")
    home.add_child(instance=contact)
    contact.refresh_from_db()

    # Create blog posts (these will be at depth 4)
    post1 = Page(title="Post 1", slug="post-1")
    blog.add_child(instance=post1)
    post1.refresh_from_db()

    post2 = Page(title="Post 2", slug="post-2")
    blog.add_child(instance=post2)
    post2.refresh_from_db()

    # Verify depths are correct
    assert home.depth == 2, f"Home should be depth 2, got {home.depth}"
    assert about.depth == 3, f"About should be depth 3, got {about.depth}"
    assert blog.depth == 3, f"Blog should be depth 3, got {blog.depth}"
    assert post1.depth == 4, f"Post1 should be depth 4, got {post1.depth}"

    return {
        "site": default_site,
        "home": home,
        "about": about,
        "blog": blog,
        "contact": contact,
        "post1": post1,
        "post2": post2,
    }


@pytest.fixture
def second_site(db, site_root):
    """
    Create a second Wagtail site with its own page tree.

    Structure:
        Site2 Home (depth 2)
        └── Article (depth 3)
    """
    home2 = Page(title="Site2 Home", slug="site2-home")
    site_root.add_child(instance=home2)
    home2.refresh_from_db()

    article = Page(title="Article", slug="article")
    home2.add_child(instance=article)
    article.refresh_from_db()

    site2 = Site.objects.create(
        hostname="site2.localhost",
        root_page=home2,
        is_default_site=False,
        site_name="Second Site",
    )

    return {
        "site": site2,
        "home": home2,
        "article": article,
    }


@pytest.fixture
def nested_site(db, default_site):
    """
    Create a site whose root_page is at depth 3 (nested under default site's home).

    Structure:
        Home (depth 2, default site root)
        └── Microsite Home (depth 3, nested site root)
            └── Landing (depth 4)
    """
    home = default_site.root_page
    home.refresh_from_db()

    microsite_home = Page(title="Microsite Home", slug="microsite")
    home.add_child(instance=microsite_home)
    microsite_home.refresh_from_db()

    landing = Page(title="Landing", slug="landing")
    microsite_home.add_child(instance=landing)
    landing.refresh_from_db()

    nested = Site.objects.create(
        hostname="micro.localhost",
        root_page=microsite_home,
        is_default_site=False,
        site_name="Microsite",
    )

    return {
        "site": nested,
        "home": microsite_home,
        "landing": landing,
    }


@pytest.fixture
def trash_can(db, default_site):
    """Get or create the trash can for the default site."""
    from sum_core.wagtail_trash.models import TrashCan

    return TrashCan.get_or_create_for_site(default_site)


@pytest.fixture
def trashed_page(db, site_with_pages, trash_can, admin_user):
    """Create a page that has been moved to trash."""
    from sum_core.wagtail_trash.models import TrashedPageInfo

    page = site_with_pages["about"]
    original_parent = page.get_parent()
    original_slug = page.slug
    original_path = page.url_path

    # Move to trash
    page.move(trash_can, pos="last-child")
    page.slug = f"{original_slug}__trashed__123456"
    page.save()

    # Create trash info
    TrashedPageInfo.objects.create(
        page=page,
        original_parent=original_parent,
        trashed_by=admin_user,
        original_path=original_path,
        original_slug=original_slug,
        descendant_count=0,
    )

    page.refresh_from_db()
    return page
