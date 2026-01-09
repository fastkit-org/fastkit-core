import re
import unicodedata
from typing import Optional, Any

class SlugServiceMixin:
    """
    Mixin that adds slug generation to services.

    Usage:
        class ArticleService(SlugServiceMixin, AsyncBaseCrudService):
            async def before_create(self, data: dict) -> dict:
                data['slug'] = self.generate_slug(
                    data['title'],
                    slug_field='slug'
                )
                return data

    Features:
    - Auto-detects sync/async from repository
    - Ensures uniqueness
    - Appends numbers if needed: "hello-world-2"
    - Handles unicode
    - Single clean method
    """

    @staticmethod
    def slugify(text: str, separator: str = '-', max_length: int = 255) -> str:
        """
        Convert text to URL-safe slug.

        Args:
            text: Text to convert
            separator: Separator character (default: '-')
            max_length: Maximum slug length (default: 245, reserves 10 for counter)

        Returns:
            URL-safe slug

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

        # Limit length
        if len(text) > max_length:
            text = text[:max_length].rsplit(separator, 1)[0]

        return text

    async def async_generate_slug(
            self,
            text: str,
            slug_field: str = 'slug',
            exclude_id: Optional[Any] = None,
            separator: str = '-'
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

        Returns:
            Unique slug

        Example:
            # In before_create hook
            async def before_create(self, data: dict) -> dict:
                data['slug'] = await self.generate_slug(data['title'])
                return data

            # In before_update hook
            async def before_update(self, id: int, data: dict) -> dict:
                if 'title' in data:
                    data['slug'] = await self.generate_slug(
                        data['title'],
                        exclude_id=id  # Don't count current record
                    )
                return data

            # Custom slug field
            data['url_slug'] = await self.generate_slug(
                data['name'],
                slug_field='url_slug'
            )
        """
        if not hasattr(self, 'repository'):
            raise AttributeError("Service must have 'repository' attribute")

        # Generate base slug
        base_slug = self.slugify(text, separator=separator)

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
            separator: str = '-'
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

        Returns:
            Unique slug

        Example:
            # In sync service
            def before_create(self, data: dict) -> dict:
                data['slug'] = self.generate_slug_sync(data['title'])
                return data
        """
        if not hasattr(self, 'repository'):
            raise AttributeError("Service must have 'repository' attribute")

        # Generate base slug
        base_slug = self.slugify(text, separator=separator)

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

