from datetime import date, time, timedelta
from app.models.models import GamingOption, BusinessSetting
from app.services import booking_service as bs


def _seed_basic(db_session):
    game = GamingOption(name="PS5", description="Test", price_per_hour=500, capacity=1)
    db_session.add(game)
    biz = BusinessSetting(opening_time=time(12, 0), closing_time=time(23, 59))
    db_session.add(biz)
    db_session.commit()
    db_session.refresh(game)
    return game


def _tomorrow():
    return date.today() + timedelta(days=1)


def test_gaming_options_seed(db_session):
    _seed_basic(db_session)
    options = bs.get_active_gaming_options(db_session)
    assert len(options) == 1
    assert options[0].name == "PS5"


def test_price_calculation(db_session):
    game = _seed_basic(db_session)
    assert bs.calculate_price(game, 2) == 1000


def test_booking_creation(db_session):
    game = _seed_basic(db_session)
    booking = bs.create_booking(db_session, "Ali", "923001234567", game.id, _tomorrow(), time(19, 0), 2)
    assert booking.booking_ref.startswith("ODG-")
    assert booking.price == 1000
    assert booking.status.value == "confirmed"


def test_overlapping_booking_rejected(db_session):
    game = _seed_basic(db_session)
    bs.create_booking(db_session, "Ali", "923001234567", game.id, _tomorrow(), time(19, 0), 2)  # 7-9 PM
    try:
        bs.create_booking(db_session, "Sara", "923009876543", game.id, _tomorrow(), time(20, 0), 2)  # 8-10 PM overlaps
        assert False, "Expected BookingError"
    except bs.BookingError as e:
        assert "already booked" in e.message


def test_non_overlapping_booking_accepted(db_session):
    game = _seed_basic(db_session)
    bs.create_booking(db_session, "Ali", "923001234567", game.id, _tomorrow(), time(19, 0), 2)  # 7-9 PM
    booking2 = bs.create_booking(db_session, "Sara", "923009876543", game.id, _tomorrow(), time(21, 0), 2)  # 9-11 PM ok
    assert booking2.status.value == "confirmed"


def test_cancellation_frees_slot(db_session):
    game = _seed_basic(db_session)
    b1 = bs.create_booking(db_session, "Ali", "923001234567", game.id, _tomorrow(), time(19, 0), 2)
    bs.cancel_booking(db_session, b1.booking_ref, "923001234567")
    booking2 = bs.create_booking(db_session, "Sara", "923009876543", game.id, _tomorrow(), time(19, 0), 2)
    assert booking2.status.value == "confirmed"


def test_reschedule_booking(db_session):
    game = _seed_basic(db_session)
    b1 = bs.create_booking(db_session, "Ali", "923001234567", game.id, _tomorrow(), time(19, 0), 2)
    updated = bs.reschedule_booking(db_session, b1.booking_ref, "923001234567", _tomorrow(), time(15, 0))
    assert updated.start_time == time(15, 0)


def test_business_hours_rejects_early_booking(db_session):
    game = _seed_basic(db_session)
    try:
        bs.create_booking(db_session, "Ali", "923001234567", game.id, _tomorrow(), time(2, 0), 1)
        assert False, "Expected BookingError for outside business hours"
    except bs.BookingError:
        pass


def test_past_booking_rejected(db_session):
    game = _seed_basic(db_session)
    yesterday = date.today() - timedelta(days=1)
    try:
        bs.create_booking(db_session, "Ali", "923001234567", game.id, yesterday, time(19, 0), 1)
        assert False, "Expected BookingError for past booking"
    except bs.BookingError:
        pass


def test_booking_ref_format(db_session):
    game = _seed_basic(db_session)
    booking = bs.create_booking(db_session, "Ali", "923001234567", game.id, _tomorrow(), time(19, 0), 1)
    parts = booking.booking_ref.split("-")
    assert parts[0] == "ODG"
    assert len(parts[1]) == 8
    assert len(parts[2]) == 4
