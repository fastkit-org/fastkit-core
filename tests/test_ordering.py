"""
Tests for multi-field ordering feature (0.4.0).

Covers _apply_ordering() in Repository and AsyncRepository,
and _order_by propagation through filter(), get_all(),
first(), paginate() and their service-layer equivalents.
"""

import pytest
import pytest_asyncio

from decimal import Decimal

from sqlalchemy import String, Integer, create_engine
from sqlalchemy.orm import Mapped, mapped_column, sessionmaker
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from fastkit_core.database import Base, IntIdMixin, TimestampMixin, Repository, AsyncRepository


# ============================================================================
# Test Models
# ============================================================================

class OrderingUser(Base, IntIdMixin):
    """Simple model for ordering tests."""
    __tablename__ = 'ordering_users'

    name: Mapped[str] = mapped_column(String(100))
    age: Mapped[int] = mapped_column(Integer)
    score: Mapped[int] = mapped_column(Integer, default=0)
    department: Mapped[str] = mapped_column(String(50), default='engineering')


# ============================================================================
# Sync Fixtures
# ============================================================================

@pytest.fixture(scope='function')
def engine():
    eng = create_engine('sqlite:///:memory:', echo=False)
    Base.metadata.create_all(eng)
    yield eng
    eng.dispose()


@pytest.fixture(scope='function')
def session(engine):
    Session = sessionmaker(bind=engine)
    s = Session()
    yield s
    s.rollback()
    s.close()


@pytest.fixture(scope='function')
def repo(session):
    return Repository(OrderingUser, session)


@pytest.fixture(scope='function')
def users(repo):
    """
    Seed 6 users designed to expose ordering edge cases:

    id | name    | age | score | department
    ---+---------+-----+-------+-----------
     1 | Alice   |  25 |    90 | engineering
     2 | Bob     |  30 |    90 | marketing
     3 | Charlie |  25 |    70 | engineering
     4 | David   |  35 |    80 | marketing
     5 | Eve     |  30 |    70 | engineering
     6 | Frank   |  35 |    90 | marketing
    """
    return repo.create_many([
        {'name': 'Alice',   'age': 25, 'score': 90, 'department': 'engineering'},
        {'name': 'Bob',     'age': 30, 'score': 90, 'department': 'marketing'},
        {'name': 'Charlie', 'age': 25, 'score': 70, 'department': 'engineering'},
        {'name': 'David',   'age': 35, 'score': 80, 'department': 'marketing'},
        {'name': 'Eve',     'age': 30, 'score': 70, 'department': 'engineering'},
        {'name': 'Frank',   'age': 35, 'score': 90, 'department': 'marketing'},
    ])


# ============================================================================
# Async Fixtures
# ============================================================================

@pytest_asyncio.fixture(scope='function')
async def async_engine():
    eng = create_async_engine('sqlite+aiosqlite:///:memory:', echo=False)
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture(scope='function')
async def async_session(async_engine):
    factory = async_sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as s:
        yield s
        await s.rollback()


@pytest_asyncio.fixture(scope='function')
async def async_repo(async_session):
    return AsyncRepository(OrderingUser, async_session)


@pytest_asyncio.fixture(scope='function')
async def async_users(async_repo):
    return await async_repo.create_many([
        {'name': 'Alice',   'age': 25, 'score': 90, 'department': 'engineering'},
        {'name': 'Bob',     'age': 30, 'score': 90, 'department': 'marketing'},
        {'name': 'Charlie', 'age': 25, 'score': 70, 'department': 'engineering'},
        {'name': 'David',   'age': 35, 'score': 80, 'department': 'marketing'},
        {'name': 'Eve',     'age': 30, 'score': 70, 'department': 'engineering'},
        {'name': 'Frank',   'age': 35, 'score': 90, 'department': 'marketing'},
    ])


# ============================================================================
# Sync — _apply_ordering unit tests
# ============================================================================

class TestApplyOrdering:
    """Direct unit tests for _apply_ordering helper (sync)."""

    def test_none_returns_query_unchanged(self, repo, session):
        """None should not modify the query."""
        from sqlalchemy import select
        q = select(OrderingUser)
        result = repo._apply_ordering(q, None)
        assert str(result) == str(q)

    def test_empty_string_is_skipped(self, repo, users):
        """Empty string field should be silently ignored."""
        # Should not raise, just return all records
        result = repo.filter(_order_by='')
        assert len(result) == 6

    def test_unknown_field_is_silently_ignored(self, repo, users):
        """Non-existent field in _order_by list is skipped, no exception."""
        result = repo.filter(_order_by='nonexistent_column')
        assert len(result) == 6  # All records still returned

    def test_unknown_field_in_list_is_silently_ignored(self, repo, users):
        """Non-existent field inside list is skipped, valid fields applied."""
        result = repo.filter(_order_by=['nonexistent_column', 'age'])
        ages = [u.age for u in result]
        assert ages == sorted(ages)

    def test_single_string_asc(self, repo, users):
        """Single string without '-' → ASC."""
        result = repo.filter(_order_by='age')
        ages = [u.age for u in result]
        assert ages == sorted(ages)

    def test_single_string_desc(self, repo, users):
        """Single string with '-' prefix → DESC."""
        result = repo.filter(_order_by='-age')
        ages = [u.age for u in result]
        assert ages == sorted(ages, reverse=True)

    def test_list_with_one_element_asc(self, repo, users):
        """List with single element → same as string."""
        result = repo.filter(_order_by=['age'])
        ages = [u.age for u in result]
        assert ages == sorted(ages)

    def test_list_with_one_element_desc(self, repo, users):
        """List with single DESC element."""
        result = repo.filter(_order_by=['-age'])
        ages = [u.age for u in result]
        assert ages == sorted(ages, reverse=True)


# ============================================================================
# Sync — multi-field ordering scenarios
# ============================================================================

class TestSyncMultiFieldOrdering:
    """Multi-field ordering through filter(), get_all(), first(), paginate()."""

    def test_two_fields_asc_asc(self, repo, users):
        """ORDER BY age ASC, name ASC."""
        result = repo.filter(_order_by=['age', 'name'])

        # age groups: 25, 25, 30, 30, 35, 35
        assert result[0].age == 25
        assert result[1].age == 25
        # Within age=25, Alice (A) before Charlie (C)
        assert result[0].name == 'Alice'
        assert result[1].name == 'Charlie'

        assert result[2].age == 30
        assert result[2].name == 'Bob'
        assert result[3].name == 'Eve'

        assert result[4].age == 35
        assert result[4].name == 'David'
        assert result[5].name == 'Frank'

    def test_two_fields_asc_desc(self, repo, users):
        """ORDER BY age ASC, score DESC."""
        result = repo.filter(_order_by=['age', '-score'])

        # age=25: Alice(90) before Charlie(70)
        assert result[0].name == 'Alice'
        assert result[1].name == 'Charlie'

        # age=30: Bob(90) before Eve(70)
        assert result[2].name == 'Bob'
        assert result[3].name == 'Eve'

        # age=35: Frank(90) before David(80)
        assert result[4].name == 'Frank'
        assert result[5].name == 'David'

    def test_two_fields_desc_asc(self, repo, users):
        """ORDER BY age DESC, name ASC."""
        result = repo.filter(_order_by=['-age', 'name'])

        # age=35 first: David before Frank
        assert result[0].age == 35
        assert result[0].name == 'David'
        assert result[1].name == 'Frank'

        # age=30: Bob before Eve
        assert result[2].age == 30
        assert result[2].name == 'Bob'
        assert result[3].name == 'Eve'

        # age=25: Alice before Charlie
        assert result[4].age == 25
        assert result[4].name == 'Alice'
        assert result[5].name == 'Charlie'

    def test_two_fields_desc_desc(self, repo, users):
        """ORDER BY age DESC, score DESC."""
        result = repo.filter(_order_by=['-age', '-score'])

        # age=35: Frank(90) before David(80)
        assert result[0].name == 'Frank'
        assert result[1].name == 'David'

        # age=30: Bob(90) before Eve(70)
        assert result[2].name == 'Bob'
        assert result[3].name == 'Eve'

        # age=25: Alice(90) before Charlie(70)
        assert result[4].name == 'Alice'
        assert result[5].name == 'Charlie'

    def test_three_fields(self, repo, users):
        """ORDER BY department ASC, age ASC, name ASC."""
        result = repo.filter(_order_by=['department', 'age', 'name'])

        # department=engineering: Alice(25), Charlie(25), Eve(30)
        eng = [u for u in result if u.department == 'engineering']
        assert eng[0].name == 'Alice'
        assert eng[1].name == 'Charlie'
        assert eng[2].name == 'Eve'

        # department=marketing: Bob(30), David(35), Frank(35)
        mkt = [u for u in result if u.department == 'marketing']
        assert mkt[0].name == 'Bob'
        assert mkt[1].name == 'David'
        assert mkt[2].name == 'Frank'

    # ------------------------------------------------------------------
    # Backward compatibility — existing single-string usage must not break
    # ------------------------------------------------------------------

    def test_backward_compat_single_string_still_works(self, repo, users):
        """Single-string _order_by must remain fully backward compatible."""
        result_str = repo.filter(_order_by='age')
        result_list = repo.filter(_order_by=['age'])
        assert [u.id for u in result_str] == [u.id for u in result_list]

    def test_backward_compat_desc_string_still_works(self, repo, users):
        result_str = repo.filter(_order_by='-score')
        result_list = repo.filter(_order_by=['-score'])
        assert [u.id for u in result_str] == [u.id for u in result_list]

    # ------------------------------------------------------------------
    # get_all()
    # ------------------------------------------------------------------

    def test_get_all_multi_field(self, repo, users):
        """get_all() should accept list _order_by."""
        result = repo.get_all(_order_by=['-score', 'name'])
        # score=90: Alice, Bob, Frank  then score=80: David  then score=70: Charlie, Eve
        scores = [u.score for u in result]
        assert scores == sorted(scores, reverse=True) or all(
            scores[i] >= scores[i + 1] for i in range(len(scores) - 1)
        )

    def test_get_all_single_string(self, repo, users):
        """get_all() single string _order_by still works."""
        result = repo.get_all(_order_by='name')
        names = [u.name for u in result]
        assert names == sorted(names)

    # ------------------------------------------------------------------
    # first()
    # ------------------------------------------------------------------

    def test_first_with_multi_field_order(self, repo, users):
        """first() should return the first record after multi-field sort."""
        first = repo.first(_order_by=['-age', '-score'])
        # Oldest (35) with highest score (90) = Frank
        assert first.name == 'Frank'

    def test_first_single_string_still_works(self, repo, users):
        result = repo.first(_order_by='age')
        assert result.age == 25

    # ------------------------------------------------------------------
    # paginate()
    # ------------------------------------------------------------------

    def test_paginate_multi_field_order(self, repo, users):
        """paginate() should respect multi-field _order_by."""
        page1, meta = repo.paginate(page=1, per_page=2, _order_by=['age', 'name'])

        assert meta['total'] == 6
        assert len(page1) == 2
        assert page1[0].name == 'Alice'
        assert page1[1].name == 'Charlie'

    def test_paginate_page2_multi_field_order(self, repo, users):
        items, meta = repo.paginate(page=2, per_page=2, _order_by=['age', 'name'])

        assert items[0].name == 'Bob'
        assert items[1].name == 'Eve'

    def test_paginate_single_string_still_works(self, repo, users):
        items, meta = repo.paginate(page=1, per_page=3, _order_by='-age')
        ages = [u.age for u in items]
        assert ages == sorted(ages, reverse=True)

    # ------------------------------------------------------------------
    # filter() combined with filters + multi-field ordering
    # ------------------------------------------------------------------

    def test_filter_with_condition_and_multi_order(self, repo, users):
        """Multi-field ordering should work alongside field filters."""
        result = repo.filter(department='marketing', _order_by=['-age', '-score'])

        assert all(u.department == 'marketing' for u in result)
        # Frank(35,90), David(35,80), Bob(30,90)
        assert result[0].name == 'Frank'
        assert result[1].name == 'David'
        assert result[2].name == 'Bob'

    def test_filter_operator_and_multi_order(self, repo, users):
        """Django-style operator filter + multi-field ordering."""
        result = repo.filter(age__gte=30, _order_by=['-score', 'name'])

        assert all(u.age >= 30 for u in result)
        scores = [u.score for u in result]
        # Must be non-increasing
        assert all(scores[i] >= scores[i + 1] for i in range(len(scores) - 1))


# ============================================================================
# Async — _apply_ordering unit tests
# ============================================================================

class TestAsyncApplyOrdering:
    """Direct unit tests for _apply_ordering helper (async)."""

    @pytest.mark.asyncio
    async def test_none_returns_query_unchanged(self, async_repo):
        from sqlalchemy import select
        q = select(OrderingUser)
        result = async_repo._apply_ordering(q, None)
        assert str(result) == str(q)

    @pytest.mark.asyncio
    async def test_unknown_field_silently_ignored(self, async_repo, async_users):
        result = await async_repo.filter(_order_by='nonexistent_column')
        assert len(result) == 6

    @pytest.mark.asyncio
    async def test_unknown_field_in_list_silently_ignored(self, async_repo, async_users):
        result = await async_repo.filter(_order_by=['nonexistent_column', 'age'])
        ages = [u.age for u in result]
        assert ages == sorted(ages)


# ============================================================================
# Async — multi-field ordering scenarios
# ============================================================================

class TestAsyncMultiFieldOrdering:
    """Multi-field ordering through async filter(), get_all(), first(), paginate()."""

    @pytest.mark.asyncio
    async def test_two_fields_asc_asc(self, async_repo, async_users):
        result = await async_repo.filter(_order_by=['age', 'name'])

        assert result[0].name == 'Alice'
        assert result[1].name == 'Charlie'
        assert result[2].name == 'Bob'
        assert result[3].name == 'Eve'
        assert result[4].name == 'David'
        assert result[5].name == 'Frank'

    @pytest.mark.asyncio
    async def test_two_fields_asc_desc(self, async_repo, async_users):
        result = await async_repo.filter(_order_by=['age', '-score'])

        assert result[0].name == 'Alice'   # age=25, score=90
        assert result[1].name == 'Charlie' # age=25, score=70
        assert result[2].name == 'Bob'     # age=30, score=90
        assert result[3].name == 'Eve'     # age=30, score=70
        assert result[4].name == 'Frank'   # age=35, score=90
        assert result[5].name == 'David'   # age=35, score=80

    @pytest.mark.asyncio
    async def test_two_fields_desc_asc(self, async_repo, async_users):
        result = await async_repo.filter(_order_by=['-age', 'name'])

        assert result[0].name == 'David'
        assert result[1].name == 'Frank'
        assert result[2].name == 'Bob'
        assert result[3].name == 'Eve'
        assert result[4].name == 'Alice'
        assert result[5].name == 'Charlie'

    @pytest.mark.asyncio
    async def test_two_fields_desc_desc(self, async_repo, async_users):
        result = await async_repo.filter(_order_by=['-age', '-score'])

        assert result[0].name == 'Frank'
        assert result[1].name == 'David'
        assert result[2].name == 'Bob'
        assert result[3].name == 'Eve'
        assert result[4].name == 'Alice'
        assert result[5].name == 'Charlie'

    @pytest.mark.asyncio
    async def test_three_fields(self, async_repo, async_users):
        result = await async_repo.filter(_order_by=['department', 'age', 'name'])

        eng = [u for u in result if u.department == 'engineering']
        assert eng[0].name == 'Alice'
        assert eng[1].name == 'Charlie'
        assert eng[2].name == 'Eve'

        mkt = [u for u in result if u.department == 'marketing']
        assert mkt[0].name == 'Bob'
        assert mkt[1].name == 'David'
        assert mkt[2].name == 'Frank'

    # ------------------------------------------------------------------
    # Backward compatibility
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_backward_compat_single_string(self, async_repo, async_users):
        result_str = await async_repo.filter(_order_by='age')
        result_list = await async_repo.filter(_order_by=['age'])
        assert [u.id for u in result_str] == [u.id for u in result_list]

    @pytest.mark.asyncio
    async def test_backward_compat_desc_string(self, async_repo, async_users):
        result_str = await async_repo.filter(_order_by='-score')
        result_list = await async_repo.filter(_order_by=['-score'])
        assert [u.id for u in result_str] == [u.id for u in result_list]

    # ------------------------------------------------------------------
    # get_all()
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_get_all_multi_field(self, async_repo, async_users):
        result = await async_repo.get_all(_order_by=['-score', 'name'])
        scores = [u.score for u in result]
        assert all(scores[i] >= scores[i + 1] for i in range(len(scores) - 1))

    @pytest.mark.asyncio
    async def test_get_all_single_string(self, async_repo, async_users):
        result = await async_repo.get_all(_order_by='name')
        names = [u.name for u in result]
        assert names == sorted(names)

    # ------------------------------------------------------------------
    # first()
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_first_with_multi_field_order(self, async_repo, async_users):
        first = await async_repo.first(_order_by=['-age', '-score'])
        assert first.name == 'Frank'

    @pytest.mark.asyncio
    async def test_first_single_string(self, async_repo, async_users):
        result = await async_repo.first(_order_by='age')
        assert result.age == 25

    # ------------------------------------------------------------------
    # paginate()
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_paginate_multi_field_order(self, async_repo, async_users):
        page1, meta = await async_repo.paginate(page=1, per_page=2, _order_by=['age', 'name'])

        assert meta['total'] == 6
        assert len(page1) == 2
        assert page1[0].name == 'Alice'
        assert page1[1].name == 'Charlie'

    @pytest.mark.asyncio
    async def test_paginate_page2_multi_field_order(self, async_repo, async_users):
        items, _ = await async_repo.paginate(page=2, per_page=2, _order_by=['age', 'name'])

        assert items[0].name == 'Bob'
        assert items[1].name == 'Eve'

    @pytest.mark.asyncio
    async def test_paginate_single_string_still_works(self, async_repo, async_users):
        items, _ = await async_repo.paginate(page=1, per_page=3, _order_by='-age')
        ages = [u.age for u in items]
        assert ages == sorted(ages, reverse=True)

    # ------------------------------------------------------------------
    # Combined filter + ordering
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_filter_with_condition_and_multi_order(self, async_repo, async_users):
        result = await async_repo.filter(department='marketing', _order_by=['-age', '-score'])

        assert all(u.department == 'marketing' for u in result)
        assert result[0].name == 'Frank'
        assert result[1].name == 'David'
        assert result[2].name == 'Bob'

    @pytest.mark.asyncio
    async def test_filter_operator_and_multi_order(self, async_repo, async_users):
        result = await async_repo.filter(age__gte=30, _order_by=['-score', 'name'])

        assert all(u.age >= 30 for u in result)
        scores = [u.score for u in result]
        assert all(scores[i] >= scores[i + 1] for i in range(len(scores) - 1))
