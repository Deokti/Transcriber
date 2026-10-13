"""«Хранилище» считает место честно и удаляет только своё (FR-25).

Две ловушки, ради которых тест и написан.

Первая — двойной счёт. В кеше HuggingFace слепок модели состоит из ссылок
на блобы. Обход, который идёт по ссылкам, насчитал бы каждый гигабайт
дважды, и экран врал бы о том, сколько место освободится.

Вторая — чужое. Папка моделей бывает общей: у нас на машине это кеш
HuggingFace, где рядом лежат модели других программ. Удаление нашей модели
не должно задеть ни их, ни соседнюю модель с похожим именем.

Папки поддельные, файлы — нужного размера. Ссылки делаем, если система
разрешает; если нет — эта часть проверки пропускается с пометкой.
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

import harness   # ставит корень проекта в путь импорта  # noqa: F401

from core.env import models, storage
from core.platform import Paths

BLOB = 10_000


def nest(root: Path, model_id: str) -> Path:
    return root / ("models--" + models.repo(model_id).replace("/", "--"))


def main() -> int:
    root = Path(tempfile.mkdtemp(prefix="transcriber-storage-"))
    cache = root / "hub"
    problems: list[str] = []

    # Наша модель целиком: блоб и слепок со ссылкой на него
    tiny = nest(cache, "tiny")
    (tiny / "blobs").mkdir(parents=True)
    blob = tiny / "blobs" / "abc123"
    blob.write_bytes(b"x" * BLOB)
    snapshot = tiny / "snapshots" / "rev1"
    snapshot.mkdir(parents=True)
    linked = True
    try:
        os.symlink(blob, snapshot / "model.bin")
    except OSError:
        linked = False
        (snapshot / "model.bin").write_bytes(b"x" * BLOB)   # так HF делает без ссылок
        blob.unlink()
    for part in ("config.json", "tokenizer.json"):
        (snapshot / part).write_bytes(b"{}")

    # Оборванная загрузка: место занято, открыть нельзя
    base = nest(cache, "base")
    (base / "blobs").mkdir(parents=True)
    (base / "blobs" / "def.incomplete").write_bytes(b"y" * 3_000)

    # Чужая модель в той же папке и соседка с похожим именем
    foreign = cache / "models--openai--clip-vit-large-patch14"
    foreign.mkdir(parents=True)
    (foreign / "weights.bin").write_bytes(b"z" * 7_000)
    distil = nest(cache, "distil-large-v3")
    distil.mkdir(parents=True)
    (distil / "keep.bin").write_bytes(b"d" * 500)

    found = {m.id: m for m in storage.models_on_disk(cache)}
    print(f"tiny: {found['tiny'].state}, {found['tiny'].bytes} байт "
          f"(ссылки {'есть' if linked else 'система не дала — проверено без них'})")
    print(f"base: {found['base'].state}, {found['base'].bytes} байт")
    print("чужих гнёзд в папке:", storage.foreign_models(cache))

    if found["tiny"].state != storage.READY:
        problems.append("целая модель не признана готовой")
    if found["tiny"].bytes != BLOB + 4:
        problems.append(f"tiny весит {found['tiny'].bytes}, а должна {BLOB + 4} "
                        "— счёт через ссылки")
    if found["base"].state != storage.PARTIAL:
        problems.append("оборванная загрузка не отличена от целой модели")
    if storage.foreign_models(cache) != 1:
        problems.append("не замечено, что папка моделей общая")

    freed = storage.remove_model("tiny", cache)
    print("удалили tiny: освобождено", freed, "байт | чужая на месте:", foreign.exists(),
          "| distil на месте:", distil.exists(), "| base на месте:", base.exists())
    if tiny.exists() or freed != BLOB + 4:
        problems.append("tiny удалена не целиком или освобождённое посчитано неверно")
    if not (foreign.exists() and distil.exists() and base.exists()):
        problems.append("удаление задело чужое")

    try:
        storage.remove_model("clip-vit-large-patch14", cache)
        problems.append("удалось удалить модель не из каталога")
    except ValueError:
        pass

    paths = Paths(root, root / "bin", cache, root / "temp",
                  root / "logs", root / "profiles").ensure()
    (paths.temp / "lecture_16k.wav").write_bytes(b"w" * 2_000)
    print("очистка temp: освобождено", storage.clear(paths.temp, paths), "байт")
    try:
        storage.clear(cache, paths)
        problems.append("удалось очистить папку моделей как служебную")
    except ValueError:
        pass

    if problems:
        print("ПРОВАЛ:", "; ".join(problems))
        return 1
    print("УСПЕХ: место считается без двойного счёта, удаляется только своё")
    return 0


if __name__ == "__main__":
    sys.exit(main())
