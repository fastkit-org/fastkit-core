import re
import unicodedata
from typing import Optional, Any


class SlugServiceMixin:
    """
    Mixin that adds slug generation to services.

    Usage:
        # Async service
        class ArticleService(SlugServiceMixin, AsyncBaseCrudService):
            async def before_create(self, data: dict) -> dict:
                data['slug'] = await self.async_generate_slug(data['title'])
                return data

        # Sync service
        class ArticleService(SlugServiceMixin, BaseCrudService):
            def before_create(self, data: dict) -> dict:
                data['slug'] = self.generate_slug(data['title'])
                return data

    Features:
    - Ensures uniqueness
    - Appends numbers if needed: "hello-world-2"
    - Handles unicode
    - Simple API
    """

    @staticmethod
    def slugify(text: str, separator: str = '-', max_length: int = 255) -> str:
        """
        Convert text to URL-safe slug.

        Args:
            text: Text to convert
            separator: Separator character (default: '-')
            max_length: Maximum slug length

        Returns:
            URL-safe slug

        Example:
            slugify("Hello World!")
            # "hello-world"
        """
        if not text:
            return ''

        # Convert to ASCII
        text = unicodedata.normalize('NFKD', text)
        text = text.encode('ascii', 'ignore').decode('ascii')

        # Lowercase
        text = text.lower()

        # Replace spaces and special chars with separator
        text = re.sub(r'[^\w\s-]', '', text)
        text = re.sub(r'[\s_-]+', separator, text)

        # Remove leading/trailing separators
        text = text.strip(separator)

        # Limit length (reserve 10 chars for counter suffix)
        max_base_length = max_length - 10
        if len(text) > max_base_length:
            text = text[:max_base_length].rsplit(separator, 1)[0]

        return text

    async def async_generate_slug(
            self,
            text: str,
            slug_field: str = 'slug',
            exclude_id: Optional[Any] = None,
            separator: str = '-',
            max_length: int = 255
    ) -> str:
        """
        Generate unique slug (async version).

        Works with AsyncRepository.
        Ensures uniqueness by checking database and appending numbers if needed.

        Args:
            text: Source text to generate slug from
            slug_field: Name of slug field in model (default: 'slug')
            exclude_id: ID to exclude from uniqueness check (for updates)
            separator: Separator character (default: '-')
            max_length: Maximum slug length (default: 255)

        Returns:
            Unique slug

        Example:
            # In before_create hook
            async def before_create(self, data: dict) -> dict:
                data['slug'] = await self.async_generate_slug(data['title'])
                return data

            # In before_update hook
            async def before_update(self, id: int, data: dict) -> dict:
                if 'title' in data:
                    data['slug'] = await self.async_generate_slug(
                        data['title'],
                        exclude_id=id
                    )
                return data

            # Custom slug field
            data['url_slug'] = await self.async_generate_slug(
                data['name'],
                slug_field='url_slug'
            )
        """
        if not hasattr(self, 'repository') or self.repository is None:
            raise AttributeError("Service must have 'repository' attribute")

        # Generate base slug
        base_slug = self.slugify(text, separator=separator, max_length=max_length)

        if not base_slug:
            raise ValueError(f"Cannot generate slug from empty text: '{text}'")

        slug = base_slug
        counter = 1

        # Check uniqueness and append number if needed
        while True:
            # Build filter conditions
            filters = {slug_field: slug}

            # Exclude current record if updating
            if exclude_id is not None:
                filters['id__ne'] = exclude_id

            # Check if slug exists
            exists = await self.repository.exists(**filters)

            if not exists:
                return slug

            # Slug exists, try with number
            counter += 1
            slug = f"{base_slug}{separator}{counter}"

            # Safety limit to prevent infinite loops
            if counter > 1000:
                # Add random suffix if too many duplicates
                import uuid
                slug = f"{base_slug}{separator}{uuid.uuid4().hex[:8]}"
                break

        return slug

    def generate_slug(
            self,
            text: str,
            slug_field: str = 'slug',
            exclude_id: Optional[Any] = None,
            separator: str = '-',
            max_length: int = 255
    ) -> str:
        """
        Generate unique slug (sync version).

        Works with sync Repository.
        Ensures uniqueness by checking database and appending numbers if needed.

        Args:
            text: Source text to generate slug from
            slug_field: Name of slug field in model (default: 'slug')
            exclude_id: ID to exclude from uniqueness check (for updates)
            separator: Separator character (default: '-')
            max_length: Maximum slug length (default: 255)

        Returns:
            Unique slug

        Example:
            # In sync service
            def before_create(self, data: dict) -> dict:
                data['slug'] = self.generate_slug(data['title'])
                return data
        """
        if not hasattr(self, 'repository') or self.repository is None:
            raise AttributeError("Service must have 'repository' attribute")

        # Generate base slug
        base_slug = self.slugify(text, separator=separator, max_length=max_length)

        if not base_slug:
            raise ValueError(f"Cannot generate slug from empty text: '{text}'")

        slug = base_slug
        counter = 1

        # Check uniqueness and append number if needed
        while True:
            # Build filter conditions
            filters = {slug_field: slug}

            # Exclude current record if updating
            if exclude_id is not None:
                filters['id__ne'] = exclude_id

            # Check if slug exists
            exists = self.repository.exists(**filters)

            if not exists:
                return slug

            # Slug exists, try with number
            counter += 1
            slug = f"{base_slug}{separator}{counter}"

            # Safety limit to prevent infinite loops
            if counter > 1000:
                # Add random suffix if too many duplicates
                import uuid
                slug = f"{base_slug}{separator}{uuid.uuid4().hex[:8]}"
                break

        return slug