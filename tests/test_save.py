from pacman.art import SKIN_BY_KEY
from pacman.save import SaveData


def test_progression_and_records(tmp_path):
    data = SaveData()
    assert data.unlocked == 1
    for score in (100, 900, 500, 900, 300, 50, 700):
        data.add_record(0, score)
    assert data.records[0] == [900, 700, 500, 300, 100]
    data.unlock_after(0, 10)
    data.unlock_after(0, 10)  # replaying a level doesn't unlock more
    assert data.unlocked == 2
    data.unlock_after(1, 2)  # nothing after the last level
    assert data.unlocked == 2

    path = tmp_path / "save.json"
    data.write(path)
    assert SaveData.load(path) == data


def test_buying_skins():
    data = SaveData()
    neon = SKIN_BY_KEY["neon"]
    assert not data.buy(neon)
    data.fruit_bank[0], data.fruit_bank[1] = 12, 6
    assert data.buy(neon)
    assert "neon" in data.skins and data.fruit_bank[:2] == [0, 1]


def test_bad_or_foreign_files_start_fresh(tmp_path):
    path = tmp_path / "save.json"
    for content in ("not json", '{"_MainStorage__settings": {}}', '{"version": 1}'):
        path.write_text(content)
        assert SaveData.load(path) == SaveData()


def test_unknown_skin_falls_back(tmp_path):
    path = tmp_path / "save.json"
    data = SaveData(skin="neon", skins=["classic", "neon"])
    data.write(path)
    path.write_text(path.read_text().replace('"neon"', '"chrome"'))
    loaded = SaveData.load(path)
    assert loaded.skin == "classic" and loaded.skins == ["classic"]


def test_cheat_unlock_is_not_saved(tmp_path):
    path = tmp_path / "save.json"
    data = SaveData()
    data.unlock_all(10)
    data.write(path)
    assert not path.exists()
