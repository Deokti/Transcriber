"""Прогресс скачивания не удваивает размер модели.

Ошибка из настоящего прогона: на скачивание модели в 145 МБ окно
показывало 282 МБ. Библиотека заводит не один счётчик, а несколько —
«скачано байт», «собрано из кусков» и «файлов из четырёх», — и наивная
сумма считает одни и те же байты дважды.

Настоящую модель для проверки качать не нужно: достаточно позвать
счётчики так же, как их зовёт библиотека, и посмотреть на числа.
"""
import sys

import harness   # ставит корень проекта в путь импорта  # noqa: F401

from core.env.models import _reporter

MEGABYTE = 1024 * 1024
SIZE = 145 * MEGABYTE


def main() -> int:
    reports = []
    Reporter = _reporter(lambda done, total: reports.append((done, total)),
                         None, SIZE)

    # Так их создаёт huggingface_hub: два счётчика байтов на одну и ту же
    # загрузку плюс счётчик файлов.
    bytes_bar = Reporter(total=147 * MEGABYTE, unit="B", desc="Downloading bytes")
    rebuild_bar = Reporter(total=147 * MEGABYTE, unit="B",
                           desc="Reconstructing (incomplete total...)")
    files_bar = Reporter(total=4, unit="it", desc="Fetching 4 files")

    bytes_bar.update(70 * MEGABYTE)
    rebuild_bar.update(70 * MEGABYTE)
    files_bar.update(1)

    done, total = reports[-1]
    print(f"показано: {done/MEGABYTE:.0f} МБ из {total/MEGABYTE:.0f} МБ")

    problems = []
    if total > 160 * MEGABYTE:
        problems.append(f"размер удвоен: {total/MEGABYTE:.0f} МБ")
    if done > 80 * MEGABYTE:
        problems.append(f"скачанное удвоено: {done/MEGABYTE:.0f} МБ")

    # В начале известен размер только первого файла — процент не должен
    # прыгать от ста к десяти, поэтому знаменатель не меньше каталожного.
    reports.clear()
    Fresh = _reporter(lambda done, total: reports.append((done, total)), None, SIZE)
    small = Fresh(total=400 * 1024, unit="B", desc="config.json")
    small.update(400 * 1024)
    done, total = reports[-1]
    if total < SIZE:
        problems.append(f"в начале знаменатель меньше модели: {total/MEGABYTE:.0f} МБ")
    print(f"первый мелкий файл: {done/MEGABYTE:.1f} МБ из {total/MEGABYTE:.0f} МБ")

    if problems:
        print("ПРОВАЛ: " + "; ".join(problems))
        return 1
    print("УСПЕХ: прогресс скачивания считает честно")
    return 0


if __name__ == "__main__":
    sys.exit(main())
