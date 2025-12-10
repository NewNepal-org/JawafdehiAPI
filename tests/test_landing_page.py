"""
Tests for the landing page (index view).
"""
from django.test import TestCase
from django.urls import reverse


class LandingPageTest(TestCase):
    """Test the landing page content and structure."""

    def test_landing_page_renders(self):
        """Test that the landing page renders successfully."""
        response = self.client.get(reverse("index"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "index.html")

    def test_landing_page_title(self):
        """Test that the page title indicates it's the Contributor Portal."""
        response = self.client.get(reverse("index"))
        self.assertContains(response, "Jawafdehi Contributor Portal")
        self.assertContains(response, "<title>Jawafdehi Contributor Portal</title>")

    def test_landing_page_has_main_website_link(self):
        """Test that the landing page links to the main Jawafdehi website."""
        response = self.client.get(reverse("index"))
        self.assertContains(response, "https://jawafdehi.org")
        self.assertContains(
            response, 
            "The actual Jawafdehi website is located at"
        )

    def test_contributor_portal_link_present(self):
        """Test that the Contributor Portal link is present."""
        response = self.client.get(reverse("index"))
        self.assertContains(response, "/admin/")
        self.assertContains(response, "Contributor Portal")
        # Check that it appears before API Access section
        content = response.content.decode()
        contributor_portal_pos = content.find("Contributor Portal</h3>")
        api_access_pos = content.find("API Access</h3>")
        self.assertGreater(api_access_pos, contributor_portal_pos)

    def test_swagger_ui_link_present(self):
        """Test that the Swagger UI link is present."""
        response = self.client.get(reverse("index"))
        self.assertContains(response, "/api/swagger/")
        self.assertContains(response, "API Documentation (Swagger UI)")

    def test_no_direct_endpoint_links(self):
        """Test that direct API endpoint links are not present."""
        response = self.client.get(reverse("index"))
        # These endpoints should not be directly linked
        self.assertNotContains(response, "/api/allegations/")
        self.assertNotContains(response, "/api/sources/")
        self.assertNotContains(response, "Allegations Endpoint")
        self.assertNotContains(response, "Document Sources Endpoint")

    def test_nepali_text_present(self):
        """Test that the Nepali text is present."""
        response = self.client.get(reverse("index"))
        self.assertContains(response, "जवाफदेही")
        self.assertContains(response, "Holding Nepali public entities accountable")
