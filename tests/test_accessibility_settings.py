import pytest

from modules.utils import accessibility_settings as a11y


@pytest.fixture(autouse=True)
def isolated_settings(tmp_path, monkeypatch):

    monkeypatch.setattr(a11y, "SETTINGS_PATH", tmp_path / "test_settings.ini")


def test_default_ui_scale_is_normal():

    assert a11y.get_ui_scale() == 1.0


def test_set_and_get_ui_scale_roundtrip():

    a11y.set_ui_scale(1.4)

    assert a11y.get_ui_scale() == 1.4


def test_default_high_contrast_is_off_with_standard_palette():

    assert a11y.is_high_contrast() is False
    assert a11y.get_ok_color_rgb() == a11y.STANDARD_OK_RGB
    assert a11y.get_ng_color_rgb() == a11y.STANDARD_NG_RGB


def test_high_contrast_switches_to_colorblind_safe_palette():

    a11y.set_high_contrast(True)

    assert a11y.is_high_contrast() is True
    assert a11y.get_ok_color_rgb() == a11y.HIGH_CONTRAST_OK_RGB
    assert a11y.get_ng_color_rgb() == a11y.HIGH_CONTRAST_NG_RGB


def test_ok_and_ng_colors_are_always_distinct():

    for high_contrast in (False, True):

        a11y.set_high_contrast(high_contrast)

        assert a11y.get_ok_color_rgb() != a11y.get_ng_color_rgb()


def test_bgr_is_reverse_of_rgb():

    rgb = a11y.get_ok_color_rgb()
    bgr = a11y.get_ok_color_bgr()

    assert bgr == tuple(reversed(rgb))


def test_light_variant_is_lighter_than_base():

    base = a11y.get_ng_color_rgb()
    light = a11y.get_ng_color_light_rgb()

    assert all(l >= b for l, b in zip(light, base))
    assert light != base


class _FakeFont:

    def __init__(self):
        self.point_size = None

    def setPointSizeF(self, value):
        self.point_size = value


class _FakeApp:

    def __init__(self):
        self._font = _FakeFont()

    def font(self):
        return self._font

    def setFont(self, font):
        self._font = font


def test_apply_ui_scale_sets_scaled_font_size():

    a11y.set_ui_scale(1.2)

    app = _FakeApp()
    a11y.apply_ui_scale(app)

    assert app.font().point_size == pytest.approx(
        a11y.BASE_FONT_POINT_SIZE * 1.2
    )
