import asyncio
import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from aiogram import Bot, Dispatcher, F
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.client.default import DefaultBotProperties

# ============================================================
# ШКОЛЬНЫЙ БОТ РАСПИСАНИЯ 1–11 КЛАССОВ + АДМИН-ПАНЕЛЬ
# aiogram 3.x
# ============================================================
# Установка:
#   pip install -U aiogram
# Запуск:
#   1) Вставь токен в BOT_TOKEN
#   2) Укажи свой Telegram ID в ADMIN_IDS
#   3) python school_schedule_bot.py
# ============================================================

BOT_TOKEN = "8639995213:AAEYyWHLo7XP5Z_vDxWbTEWjOkuDP3r0bSg"
TIMEZONE = "UTC"
ADMIN_IDS = {1094852110}  # замени на свой Telegram user_id

LESSON_TIMES = [
    ("1", "08:00", "08:45"),
    ("2", "08:55", "9:40"),
    ("3", "9:55", "10:40"),
    ("4", "10:55", "11:40"),
    ("5", "11:50", "12:35"),
    ("6", "12:45", "13:30"),
    ("7", "13:40", "14:25"),
    ("8", "14:35", "15:20"),
]

DAY_KEYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday"]
DAY_TITLES = {
    "monday": "Понедельник",
    "tuesday": "Вторник",
    "wednesday": "Среда",
    "thursday": "Четверг",
    "friday": "Пятница",
    "saturday": "Суббота",
}

TEACHERS = {
    "Ильяшенко А.В.": {
        "monday": ["1 урок — 5 класс", "2 урок — 6 класс", "3 урок — 7 класс", "4 урок — 8 класс"],
        "tuesday": ["1 урок — 9 класс", "2 урок — 10 класс", "3 урок — 11 класс"],
        "wednesday": ["2 урок — 5 класс", "3 урок — 6 класс"],
        "thursday": ["1 урок — 7 класс", "2 урок — 8 класс", "5 урок — 9 класс"],
        "friday": ["1 урок — 10 класс", "2 урок — 11 класс"],
        "saturday": [],
    },
    "Ермолова И.А.": {
        "monday": ["1 урок — 1 класс", "2 урок — 2 класс", "3 урок — 3 класс"],
        "tuesday": ["2 урок — 4 класс", "3 урок — 1 класс"],
        "wednesday": ["1 урок — 2 класс", "2 урок — 3 класс", "3 урок — 4 класс"],
        "thursday": ["1 урок — 1 класс", "2 урок — 2 класс"],
        "friday": ["1 урок — 3 класс", "2 урок — 4 класс"],
        "saturday": [],
    },
}


def generate_schedule_for_grade(grade: int) -> dict:
    base = {
        "monday": [
            f"Разговоры о важном ({grade} кл.)",
            "Русский язык",
            "Математика",
            "Литература",
            "Английский язык",
            "Физкультура",
        ],
        "tuesday": [
            "История",
            "Русский язык",
            "Информатика",
            "Математика",
            "Биология",
            "Технология",
        ],
        "wednesday": [
            "Литература",
            "География",
            "Математика",
            "Английский язык",
            "ИЗО / Музыка",
            "Классный час",
        ],
        "thursday": [
            "Русский язык",
            "Физика",
            "Математика",
            "Обществознание",
            "Информатика",
            "Физкультура",
        ],
        "friday": [
            "История",
            "Русский язык",
            "Химия",
            "Литература",
            "Английский язык",
            "ОБЖ",
        ],
        "saturday": [
            "Внеурочная деятельность",
            "Проектная работа",
            "Факультатив",
        ] if grade >= 5 else [
            "Окружающий мир",
            "Чтение",
            "Творческая мастерская",
        ],
    }

    if grade <= 4:
        base["thursday"][1] = "Окружающий мир"
        base["friday"][2] = "Технология"
    elif grade >= 9:
        base["thursday"][1] = "Физика / Подготовка к ОГЭ/ЕГЭ"
        base["friday"][2] = "Химия / Подготовка к ОГЭ/ЕГЭ"

    return base


SCHEDULE = {str(grade): generate_schedule_for_grade(grade) for grade in range(1, 12)}
SCHEDULE = {str(grade): generate_schedule_for_grade(grade) for grade in range(1, 12)}

SCHEDULE["8"] = {
    "monday": [
        "Разговоры о важном",
        "Обществознание",
        "Алгебра",
        "Русский язык",
        "Химия",
        "Физика",
        "Литература",
        "Музыка",
    ],
    "tuesday": [
        "Биология",
        "История",
        "Иностранный язык",
        "Русский язык",
        "Информатика",
        "Геометрия",
        "Математика",
    ],
    "wednesday": [
        "Физика",
        "География",
        "ОБЗР",
        "Химия",
        "Труд (технология)",
        "Иностранный язык",
        "Химия",
    ],
    "thursday": [
        "Иностранный язык",
        "Литература",
        "Русский язык",
        "Биология",
        "Геометрия",
        "Математика",
        "Профориентация",
    ],
    "friday": [
        "Вероятность и статистика",
        "Алгебра",
        "Алгебра",
        "История",
        "География",
        "Физкультура",
        "Физкультура",
    ],
    "saturday": []
}

user_state: dict[int, str] = {}
admin_mode: dict[int, dict] = {}
user_state: dict[int, str] = {}
admin_mode: dict[int, dict] = {}


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


def now_local() -> datetime:
    return datetime.now(ZoneInfo(TIMEZONE))


def get_current_day_key() -> str | None:
    weekday = now_local().weekday()
    if weekday > 5:
        return None
    return DAY_KEYS[weekday]


def time_in_range(start: str, end: str, current: str) -> bool:
    return start <= current <= end


def get_current_lesson_info(grade: str):
    day_key = get_current_day_key()
    if not day_key:
        return None, "Сегодня выходной — уроков нет ✨"

    schedule = SCHEDULE.get(grade, {})
    lessons = schedule.get(day_key, [])
    current_time = now_local().strftime("%H:%M")

    for index, (lesson_number, start, end) in enumerate(LESSON_TIMES):
        if time_in_range(start, end, current_time):
            if index < len(lessons):
                return {
                    "number": lesson_number,
                    "start": start,
                    "end": end,
                    "subject": lessons[index],
                    "day": DAY_TITLES[day_key],
                }, None
            return None, "Сейчас учебное время, но урок для этого класса не найден в расписании."

    first_start = LESSON_TIMES[0][1]
    last_end = LESSON_TIMES[len(lessons) - 1][2] if lessons else LESSON_TIMES[0][2]

    if current_time < first_start:
        return None, f"Уроки ещё не начались. Первый урок в {first_start} ⏰"
    if current_time > last_end:
        return None, "На сегодня уроки уже закончились 🎉"

    return None, "Сейчас перемена ☕"


def format_day_schedule(grade: str, day_key: str) -> str:
    lessons = SCHEDULE.get(grade, {}).get(day_key, [])
    title = DAY_TITLES[day_key]

    if not lessons:
        return f"<b>{title}</b>\n\nНа этот день расписание пока не заполнено."

    lines = [f"📚 <b>{title}</b>", f"🏫 <b>{grade} класс</b>", ""]
    for i, subject in enumerate(lessons):
        number, start, end = LESSON_TIMES[i]
        lines.append(f"<b>{number}.</b> {start}–{end} — {subject}")
    return "\n".join(lines)


def format_week_schedule(grade: str) -> str:
    lines = [f"✨ <b>Расписание на неделю</b>", f"🏫 <b>{grade} класс</b>", ""]
    for day_key in DAY_KEYS:
        lessons = SCHEDULE.get(grade, {}).get(day_key, [])
        if not lessons:
            continue
        lines.append(f"<b>{DAY_TITLES[day_key]}</b>")
        for i, subject in enumerate(lessons):
            number, start, end = LESSON_TIMES[i]
            lines.append(f"{number}. {start}–{end} — {subject}")
        lines.append("")
    return "\n".join(lines).strip()


def format_teacher_schedule(teacher_name: str, day_key: str | None = None) -> str:
    teacher = TEACHERS.get(teacher_name)
    if not teacher:
        return "Учитель не найден."

    lines = [f"👨‍🏫 <b>{teacher_name}</b>"]
    days = [day_key] if day_key else DAY_KEYS

    for dk in days:
        lessons = teacher.get(dk, [])
        lines.append("")
        lines.append(f"<b>{DAY_TITLES[dk]}</b>")
        if lessons:
            lines.extend(lessons)
        else:
            lines.append("— уроков нет")

    return "\n".join(lines)


def main_menu_kb(selected_grade: str | None = None, is_user_admin: bool = False):
    kb = InlineKeyboardBuilder()
    grade_text = f"🎓 Класс: {selected_grade}" if selected_grade else "🎓 Выбрать класс"
    kb.button(text=grade_text, callback_data="choose_grade")
    kb.button(text="📅 Расписание на сегодня", callback_data="today")
    kb.button(text="🕒 Текущий урок", callback_data="current")
    kb.button(text="🗓 Расписание на неделю", callback_data="week")
    kb.button(text="👨‍🏫 Уроки учителей", callback_data="teachers")
    kb.button(text="ℹ️ Помощь", callback_data="help")
    if is_user_admin:
        kb.button(text="⚙️ Админ-панель", callback_data="admin")
    kb.adjust(1, 2, 2, 1, 1)
    return kb.as_markup()


def grades_kb():
    kb = InlineKeyboardBuilder()
    for grade in range(1, 12):
        kb.button(text=f"{grade} класс", callback_data=f"grade:{grade}")
    kb.button(text="⬅️ Назад", callback_data="back_main")
    kb.adjust(3, 3, 3, 2, 1)
    return kb.as_markup()


def day_switcher_kb(grade: str, current_day_key: str):
    kb = InlineKeyboardBuilder()
    for day_key in DAY_KEYS:
        prefix = "✅ " if day_key == current_day_key else ""
        kb.button(text=f"{prefix}{DAY_TITLES[day_key]}", callback_data=f"day:{grade}:{day_key}")
    kb.button(text="🏠 В меню", callback_data="back_main")
    kb.adjust(2, 2, 2, 1)
    return kb.as_markup()


def teachers_kb():
    kb = InlineKeyboardBuilder()
    for name in TEACHERS:
        kb.button(text=name, callback_data=f"teacher:{name}")
    kb.button(text="🏠 В меню", callback_data="back_main")
    kb.adjust(1)
    return kb.as_markup()


def teacher_days_kb(teacher_name: str):
    kb = InlineKeyboardBuilder()
    kb.button(text="📖 Вся неделя", callback_data=f"teacher_week:{teacher_name}")
    for day_key in DAY_KEYS:
        kb.button(text=DAY_TITLES[day_key], callback_data=f"teacher_day:{teacher_name}:{day_key}")
    kb.button(text="⬅️ К учителям", callback_data="teachers")
    kb.button(text="🏠 В меню", callback_data="back_main")
    kb.adjust(1, 2, 2, 2, 1, 1)
    return kb.as_markup()


def admin_menu_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="✏️ Изменить урок класса", callback_data="admin_edit_class")
    kb.button(text="👨‍🏫 Изменить урок учителя", callback_data="admin_edit_teacher")
    kb.button(text="📋 Показать шаблон ввода", callback_data="admin_template")
    kb.button(text="🏠 В меню", callback_data="back_main")
    kb.adjust(1)
    return kb.as_markup()


router = Dispatcher()


@router.message(CommandStart())
async def cmd_start(message: Message):
    text = (
        "╔════════════════════╗\n"
        "🎓 <b>БОТ ШКОЛЬНОГО РАСПИСАНИЯ</b>\n"
        "╚════════════════════╝\n\n"
        "🌟 <b>Добро пожаловать в бот школьного расписания</b>\n\n"
        "Здесь можно быстро посмотреть:\n"
        "📚 расписание для 1–11 классов\n"
        "📅 расписание на сегодня\n"
        "🕒 текущий урок\n"
        "🗓 расписание на всю неделю\n"
        "👨‍🏫 уроки учителей\n\n"
        "✨ Нажми кнопку ниже и выбери нужный раздел\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "👨‍💻 <b>by. Neznamov Ivan</b>\n"
    )

    await message.answer(
        text,
        reply_markup=main_menu_kb(is_user_admin=is_admin(message.from_user.id)),
        parse_mode=ParseMode.HTML,
    )
    


@router.callback_query(F.data == "choose_grade")
async def choose_grade(callback: CallbackQuery):
    await callback.answer("Открываю классы... 📚")

    await callback.message.edit_text(
        "⏳ <b>Загрузка списка классов...</b>",
        parse_mode=ParseMode.HTML,
    )

    await asyncio.sleep(0.6)

    await callback.message.edit_text(
        "🎓 <b>Выбери класс</b>\n\nДоступны классы с 1 по 11.",
        reply_markup=grades_kb(),
        parse_mode=ParseMode.HTML,
    )


@router.callback_query(F.data.startswith("grade:"))
async def select_grade(callback: CallbackQuery):
    grade = callback.data.split(":")[1]
    user_state[callback.from_user.id] = grade
    await callback.message.edit_text(
        f"✅ <b>Класс выбран: {grade}</b>\n\nТеперь можно открыть нужное расписание.",
        reply_markup=main_menu_kb(grade, is_admin(callback.from_user.id)),
        parse_mode=ParseMode.HTML,
    )
    await callback.answer(f"Выбран {grade} класс")


@router.callback_query(F.data == "today")
async def show_today(callback: CallbackQuery):
    grade = user_state.get(callback.from_user.id)
    if not grade:
        await callback.answer("Сначала выбери класс", show_alert=True)
        return

    day_key = get_current_day_key()
    if not day_key:
        await callback.message.edit_text(
            f"🎉 <b>Сегодня выходной</b>\n\nДля {grade} класса уроков сегодня нет.",
            reply_markup=main_menu_kb(grade, is_admin(callback.from_user.id)),
            parse_mode=ParseMode.HTML,
        )
        await callback.answer()
        return

    await callback.message.edit_text(
        format_day_schedule(grade, day_key),
        reply_markup=day_switcher_kb(grade, day_key),
        parse_mode=ParseMode.HTML,
    )
    await callback.answer()


@router.callback_query(F.data.startswith("day:"))
async def show_day(callback: CallbackQuery):
    _, grade, day_key = callback.data.split(":")
    await callback.message.edit_text(
        format_day_schedule(grade, day_key),
        reply_markup=day_switcher_kb(grade, day_key),
        parse_mode=ParseMode.HTML,
    )
    await callback.answer()


@router.callback_query(F.data == "current")
async def show_current(callback: CallbackQuery):
    grade = user_state.get(callback.from_user.id)
    if not grade:
        await callback.answer("Сначала выбери класс", show_alert=True)
        return

    lesson, info_text = get_current_lesson_info(grade)
    if lesson:
        text = (
            f"🕒 <b>Сейчас идёт урок</b>\n\n"
            f"🏫 Класс: <b>{grade}</b>\n"
            f"📅 День: <b>{lesson['day']}</b>\n"
            f"📘 Предмет: <b>{lesson['subject']}</b>\n"
            f"🔢 Урок: <b>{lesson['number']}</b>\n"
            f"⏰ Время: <b>{lesson['start']}–{lesson['end']}</b>"
        )
    else:
        text = (
            f"🕒 <b>Информация по текущему времени</b>\n\n"
            f"🏫 Класс: <b>{grade}</b>\n{info_text}"
        )

    await callback.message.edit_text(
        text,
        reply_markup=main_menu_kb(grade, is_admin(callback.from_user.id)),
        parse_mode=ParseMode.HTML,
    )
    await callback.answer()


@router.callback_query(F.data == "week")
async def show_week(callback: CallbackQuery):
    grade = user_state.get(callback.from_user.id)
    if not grade:
        await callback.answer("Сначала выбери класс", show_alert=True)
        return

    await callback.message.edit_text(
        format_week_schedule(grade),
        reply_markup=main_menu_kb(grade, is_admin(callback.from_user.id)),
        parse_mode=ParseMode.HTML,
    )
    await callback.answer()


@router.callback_query(F.data == "teachers")
async def show_teachers(callback: CallbackQuery):
    await callback.message.edit_text(
        "👨‍🏫 <b>Уроки учителей</b>\n\nВыбери учителя.",
        reply_markup=teachers_kb(),
        parse_mode=ParseMode.HTML,
    )
    await callback.answer()


@router.callback_query(F.data.startswith("teacher:"))
async def show_teacher(callback: CallbackQuery):
    teacher_name = callback.data.split(":", 1)[1]
    await callback.message.edit_text(
        format_teacher_schedule(teacher_name),
        reply_markup=teacher_days_kb(teacher_name),
        parse_mode=ParseMode.HTML,
    )
    await callback.answer()


@router.callback_query(F.data.startswith("teacher_day:"))
async def show_teacher_day(callback: CallbackQuery):
    _, teacher_name, day_key = callback.data.split(":", 2)
    await callback.message.edit_text(
        format_teacher_schedule(teacher_name, day_key),
        reply_markup=teacher_days_kb(teacher_name),
        parse_mode=ParseMode.HTML,
    )
    await callback.answer()


@router.callback_query(F.data.startswith("teacher_week:"))
async def show_teacher_week(callback: CallbackQuery):
    teacher_name = callback.data.split(":", 1)[1]
    await callback.message.edit_text(
        format_teacher_schedule(teacher_name),
        reply_markup=teacher_days_kb(teacher_name),
        parse_mode=ParseMode.HTML,
    )
    await callback.answer()


@router.callback_query(F.data == "admin")
async def admin_panel(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    await callback.message.edit_text(
        "⚙️ <b>Админ-панель</b>\n\nЗдесь можно редактировать расписание классов и учителей.",
        reply_markup=admin_menu_kb(),
        parse_mode=ParseMode.HTML,
    )
    await callback.answer()


@router.callback_query(F.data == "admin_template")
async def admin_template(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    text = (
        "<b>Шаблоны для редактирования</b>\n\n"
        "<b>Для класса:</b>\n"
        "класс|день|номер_урока|предмет\n"
        "Пример: <code>7|monday|3|Алгебра</code>\n\n"
        "<b>Для учителя:</b>\n"
        "учитель|день|текст\n"
        "Пример: <code>Иванова А.А.|monday|3 урок — 7 класс</code>\n\n"
        "Дни недели: monday, tuesday, wednesday, thursday, friday, saturday"
    )
    await callback.message.edit_text(text, reply_markup=admin_menu_kb(), parse_mode=ParseMode.HTML)
    await callback.answer()


@router.callback_query(F.data == "admin_edit_class")
async def admin_edit_class(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    admin_mode[callback.from_user.id] = {"mode": "edit_class"}
    await callback.message.edit_text(
        "✏️ <b>Редактирование расписания класса</b>\n\n"
        "Отправь сообщение в формате:\n"
        "<code>7|monday|3|Алгебра</code>",
        reply_markup=admin_menu_kb(),
        parse_mode=ParseMode.HTML,
    )
    await callback.answer()


@router.callback_query(F.data == "admin_edit_teacher")
async def admin_edit_teacher(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    admin_mode[callback.from_user.id] = {"mode": "edit_teacher"}
    await callback.message.edit_text(
        "👨‍🏫 <b>Редактирование уроков учителя</b>\n\n"
        "Отправь сообщение в формате:\n"
        "<code>Иванова А.А.|monday|3 урок — 7 класс</code>",
        reply_markup=admin_menu_kb(),
        parse_mode=ParseMode.HTML,
    )
    await callback.answer()


@router.callback_query(F.data == "help")
async def show_help(callback: CallbackQuery):
    grade = user_state.get(callback.from_user.id)
    text = (
        "ℹ️ <b>Как пользоваться ботом</b>\n\n"
        "1. Выбери класс\n"
        "2. Используй кнопки расписания\n"
        "3. Открой раздел <b>Уроки учителей</b>, чтобы посмотреть нагрузку педагога\n\n"
        "⚙️ Для администратора доступна админ-панель с быстрым редактированием."
    )
    await callback.message.edit_text(
        text,
        reply_markup=main_menu_kb(grade, is_admin(callback.from_user.id)),
        parse_mode=ParseMode.HTML,
    )
    await callback.answer()


@router.callback_query(F.data == "back_main")
async def back_main(callback: CallbackQuery):
    grade = user_state.get(callback.from_user.id)
    await callback.message.edit_text(
        "🏠 <b>Главное меню</b>\n\nВыбирай нужный раздел кнопками ниже.",
        reply_markup=main_menu_kb(grade, is_admin(callback.from_user.id)),
        parse_mode=ParseMode.HTML,
    )
    await callback.answer()


@router.message()
async def fallback_message(message: Message):
    user_id = message.from_user.id
    if is_admin(user_id) and user_id in admin_mode:
        mode = admin_mode[user_id].get("mode")
        raw = message.text.strip()

        try:
            if mode == "edit_class":
                grade, day_key, lesson_number, subject = [x.strip() for x in raw.split("|", 3)]
                lesson_index = int(lesson_number) - 1
                if grade not in SCHEDULE:
                    raise ValueError("Такого класса нет")
                if day_key not in DAY_KEYS:
                    raise ValueError("Неверный день недели")
                lessons = SCHEDULE[grade].setdefault(day_key, [])
                while len(lessons) <= lesson_index:
                    lessons.append("---")
                lessons[lesson_index] = subject
                await message.answer(
                    f"✅ Урок обновлён\n\nКласс: {grade}\nДень: {DAY_TITLES[day_key]}\nУрок: {lesson_number}\nПредмет: {subject}",
                    reply_markup=main_menu_kb(user_state.get(user_id), is_admin(user_id)),
                    parse_mode=ParseMode.HTML,
                )
                admin_mode.pop(user_id, None)
                return

            if mode == "edit_teacher":
                teacher_name, day_key, lesson_text = [x.strip() for x in raw.split("|", 2)]
                if day_key not in DAY_KEYS:
                    raise ValueError("Неверный день недели")
                if teacher_name not in TEACHERS:
                    TEACHERS[teacher_name] = {dk: [] for dk in DAY_KEYS}
                TEACHERS[teacher_name][day_key].append(lesson_text)
                await message.answer(
                    f"✅ Урок учителя добавлен\n\nУчитель: {teacher_name}\nДень: {DAY_TITLES[day_key]}\nЗапись: {lesson_text}",
                    reply_markup=main_menu_kb(user_state.get(user_id), is_admin(user_id)),
                    parse_mode=ParseMode.HTML,
                )
                admin_mode.pop(user_id, None)
                return

        except Exception as e:
            await message.answer(
                f"❌ Ошибка: {e}\n\nПроверь формат ввода через админ-панель.",
                reply_markup=admin_menu_kb(),
                parse_mode=ParseMode.HTML,
            )
            return

    await message.answer(
        "Я работаю через кнопки 👇",
        reply_markup=main_menu_kb(user_state.get(user_id), is_admin(user_id)),
        parse_mode=ParseMode.HTML,
    )


async def main():
    if BOT_TOKEN == "PASTE_YOUR_BOT_TOKEN_HERE":
        raise ValueError("Вставь токен бота в переменную BOT_TOKEN перед запуском.")

    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    await router.start_polling(bot)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("Бот остановлен")
