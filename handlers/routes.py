from aiogram import Router, F
from aiogram.filters import Command
from config import bot
import asyncio
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton
    )
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
# from aiogram.types import FSInputFile
from datetime import datetime


class GameRegistration(StatesGroup):
    game_bauman = State()
    game_name = State()
    team_size = State()
    team_name = State()
    game_confirm = State()
    game_approval = State()


class MovieRegistration(StatesGroup):
    movie_bauman = State()
    movie_name = State()
    movie_group_number = State()
    movie_confirm = State()
    movie_approval = State()


class TripRegistration(StatesGroup):
    trip_bauman = State()
    trip_name = State()
    trip_group_number = State()
    trip_phone_number = State()
    trip_date_of_birth = State()
    trip_illness = State()
    trip_special = State()
    trip_confirm = State()
    trip_approval = State()

router = Router()

# Настройка доступа к гуглу
scope = ["https://spreadsheets.google.com/feeds",
         "https://www.googleapis.com/auth/spreadsheets",
         "https://www.googleapis.com/auth/drive.file",
         "https://www.googleapis.com/auth/drive"]

creds = ServiceAccountCredentials.from_json_keyfile_name("kinocredentials.json", scope)
client = gspread.authorize(creds)

workbook = client.open("КиношкиРега")
game_sheet = workbook.worksheet("ЛистКиноигра")
game_sheet2 = workbook.worksheet("ИграЛистОжидания")  # лист ожидания
movie_sheet = workbook.worksheet("ЛистКиновечер")
trip_sheet = workbook.worksheet("ЛистВыезд")
trip_sheet2 = workbook.worksheet("ВыездЛистОжидания")
# game_sheet.append_row(["Имя", "Команда", "Количество", "@username"])
# movie_sheet.append_row(["Имя", "Группа", "@username"])
events_sheet = workbook.worksheet("Мероприятия")


# ЦЕПОЧКА КЛАВИШ КИНОИГРЫ




def get_event_by_name(name: str):
    events = events_sheet.get_all_records()
    return next((e for e in events if e["Название"] == name), None)


def is_user_registered(sheet, user_id):
    records = sheet.get_all_records()
    return any(str(r.get("user_id")) == str(user_id) for r in records)


def append_row(sheet, row):
    sheet.append_row(row)


def get_1game_inline_keyboard():
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Назад", callback_data="info_start")],
            [InlineKeyboardButton(text="Доступные мероприятия", callback_data="available_game")],
            [InlineKeyboardButton(text="Правила на Киноигре", callback_data="game_rules")]
        ]
    )
    return keyboard


def get_2game_inline_keyboard():
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Назад", callback_data="info_start")],
            [InlineKeyboardButton(text="Зарегистрироваться", callback_data="reg_game")]
        ]
    )
    return keyboard


@router.callback_query(F.data == "available_game")
async def check_quiz_availability(callback: CallbackQuery):
    events = events_sheet.get_all_records()
    game = next((e for e in events if e["Название"] == "Киноигра"), None)

    if game and game["Доступно"].lower() == "да":
        date = game["Дата_начало"]
        time = game["Время"]
        place = game["Место"]
        await callback.message.answer(
            f"📅 Киноигра состоится {date} в {time} в {place}.\n\n Регистрация открыта!",
            reply_markup=get_2game_inline_keyboard()
        )
    else:
        await callback.message.answer("❌ Регистрация на Киноигру пока недоступна.",
                                      reply_markup=back_to_the_start())
    await callback.message.delete()


def agree_game_keyboard():
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Согласен(-на)", callback_data="game_FSM")]
        ]
    )
    return keyboard


@router.callback_query(F.data == "reg_game")
async def law_game_registration(callback: CallbackQuery):
    await callback.message.delete()
    await callback.message.answer("Перед началом — секунда формальности.\n\n"
                                  "Нам нужно твоё <b>согласие</b> на обработку персональных данных"
                                  " в соответствии с Федеральным законом от 27.07.2006 №152-ФЗ"
                                  " «О персональных данных». ",
                                  parse_mode="HTML",
                                  reply_markup=agree_game_keyboard())
    await callback.answer()


@router.callback_query(F.data == "game_FSM")
async def start_game_registration(callback: CallbackQuery, state: FSMContext):
    await state.update_data(game_approval="да")
    await callback.message.delete()
    await callback.message.answer("Все ли члены команды являются студентами МГТУ им. Н.Э. Баумана?\n\n"
                                  "Ответь 'да' или 'нет'.")
    await state.set_state(GameRegistration.game_bauman)
    await callback.answer()


@router.message(GameRegistration.game_bauman)
async def check_student_status(message: Message, state: FSMContext):
    text = message.text.strip().lower()

    if text not in ["да", "нет"]:
        await message.answer("❌ Пожалуйста, ответьте только 'да' или 'нет'.")
        return

    await state.update_data(game_bauman=text)
    await message.answer("<b>Твоё имя и фамилия, Капитан?</b>\n\n"
                         "<i>Если ты попал(-а) не туда, то в конце будет кнопка 'Отменить'"
                         " и ты вернешься в начало.</i>",
                         parse_mode="HTML")
    await state.set_state(GameRegistration.game_name)


@router.message(GameRegistration.game_name)
async def get_cap_name(message: Message, state: FSMContext):
    await state.update_data(game_name=message.text)
    await message.answer("Сколько человек в твоей команде?\nОт 4 до 8 человек")
    await state.set_state(GameRegistration.team_size)


@router.message(GameRegistration.team_size)
async def get_team_size(message: Message, state: FSMContext):
    try:
        team_size = int(message.text)
        if not 4 <= team_size <= 8:
            raise ValueError
    except ValueError:
        await message.answer("❌ Число — не подходит.\nПодумай ещё раз (от 4 до 8 человек).")
        return
    await state.update_data(team_size=team_size)
    await message.answer("Как называется твоя команда?")
    await state.set_state(GameRegistration.team_name)


@router.message(GameRegistration.team_name)
async def get_team_name(message: Message, state: FSMContext):
    await state.update_data(team_name=message.text)

    data = await state.get_data()
    game_username = message.from_user.username
    game_user_mention = f"@{game_username}" if game_username else "без username"

    summary = (
        f"📝 Вот что ты указал:\n\n"
        f"🎓 Все члены команды из МГТУ: {data['game_bauman']}\n"
        f"👤 Имя и фамилия капитана: {data['game_name']} ({game_user_mention})\n"
        f"👥 Кол-во участников: {data['team_size']}\n"
        f"🏷 Название команды: {data['team_name']}"
    )
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Начать заново", callback_data="game_restart")],
            [InlineKeyboardButton(text="Подтвердить", callback_data="game_confirm")],
            [InlineKeyboardButton(text="Отменить", callback_data="denied")]
        ]
    )
    await message.answer(summary, reply_markup=keyboard)
    await state.set_state(GameRegistration.game_confirm)


@router.callback_query(F.data == "game_confirm")
async def confirm_registration(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    user_id = callback.from_user.id
    username = callback.from_user.username or "без username"
    timestamp = datetime.now().strftime("%d.%m.%Y %H:%M")
    event = get_event_by_name("Киноигра")
    if not event:
        await callback.message.answer("Ошибка: событие не найдено.",
                                      reply_markup=back_to_the_start())
        return
    # проверка на повторную регу
    if is_user_registered(game_sheet, user_id):
        await callback.message.delete()
        await callback.message.answer("Вы уже зарегистрированы в основном списке.",
                                      reply_markup=back_to_the_start())
        return
    await callback.answer()

    if is_user_registered(game_sheet2, user_id):
        await callback.message.delete()
        await callback.message.answer("Вы уже находитесь в листе ожидания.",
                                      reply_markup=back_to_the_start())
        return
    await callback.answer()

    # считаем количество команд
    main_records = game_sheet.get_all_records()
    count = len(main_records)
    limit = int(event["Лимит"])
    row = [
        data['game_name'],
        data['team_size'],
        data['team_name'],
        f"@{username}",
        timestamp,
        user_id,
        data['game_bauman'],
        data['game_approval']
    ]
    # основной лист
    if count < limit:
        append_row(game_sheet, row)
        await callback.message.delete()
        await callback.message.answer(
            "✅ Регистрация завершена! <b>Увидимся на Киноигре!</b> 🎉",
            reply_markup=back_to_the_start(),
            parse_mode='HTML'
        )
        await state.clear()
        await callback.answer()
    else:
        # лист ожидания
        game_sheet2.append_row([
            data['game_name'], data['team_size'], data['team_name'],
            f"@{username}", timestamp, user_id, data['game_bauman'], data['game_approval']
        ])
        await callback.message.delete()
        await callback.message.answer(
            "⚠️ Основные места заняты.\n"
            "Вы зарегистрированы, но добавлены в <b>лист ожидания</b>.\n\n"
            "<b>Не спешите расстраиваться!</b>\n\n"
            "После закрытия регистрации мы начнём собирать подтверждения, "
            "как правило, некоторые команды отказываются от участия, в таком случае мы свяжемся с Вами "
            "и если Вы будете согласны, то займёте их место\n\n"
            "Благодарим за понимание!🙏",
            parse_mode="HTML",
            reply_markup=back_to_the_start()
        )
        await state.clear()
        await callback.answer()


@router.callback_query(F.data == "game_restart")
async def law_game_registration(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.delete()
    await callback.message.answer("Хорошо, давай начнём заново\n\n"
                                  "И снова формальность.\n"
                                  "Нам нужно твоё <b>согласие</b> на обработку персональных данных"
                                  " в соответствии с Федеральным законом от 27.07.2006 №152-ФЗ"
                                  " «О персональных данных». ",
                                  parse_mode="HTML",
                                  reply_markup=agree_game_keyboard())
    await callback.answer()


@router.message(F.text == "/notify_game")
async def notify_game(message: Message):
    events = events_sheet.get_all_records()

    game = next((e for e in events if e["Название"] == "Киноигра"), None)
    if not game or game["Доступно"].lower() != "да":
        await message.answer("❌ Киноигра недоступна для рассылки.")
        return

    date = game["Дата_начало"]
    time = game["Время"]
    place = game["Место"]
    # remember = game["Не забудьте"]
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Подтвердить ✅", callback_data="game_confirm_yes")],
            [InlineKeyboardButton(text="Отменить ❌", callback_data="game_confirm_no")]
        ]
    )
    rows = game_sheet.get_all_records()
    sent_count = 0
    for row in rows:
        user_id = row.get("user_id")
        if user_id:
            try:
                await bot.send_message(
                    int(user_id),
                    (
                        f"🎬 Напоминаем: <b>Киноигра</b> состоится {date} в {time} в {place}!\n"
                        f"Подтверждаете ли Вы свою регистрацию? 👇\n\n"
                        f"(Если придёте, но есть изменения,"
                        f"то <b>обязательно</b> напишите о них @planb_on_fire, a после нажмите кнопку подтвердить)\n"
                    ),
                    reply_markup=keyboard,
                    parse_mode="HTML"
                )
                sent_count += 1
                await asyncio.sleep(0.5)
            except Exception as e:
                print(f"Не удалось отправить {user_id}: {e}")
    await message.answer(f"✅ Рассылка завершена. Уведомлений отправлено: {sent_count}")


@router.callback_query(F.data == "game_confirm_yes")
async def confirm_game(callback: CallbackQuery):
    user_id = callback.from_user.id
    rows = game_sheet.get_all_records()

    for i, row in enumerate(rows, start=2):
        if str(row.get("user_id")) == str(user_id):
            game_sheet.update_cell(i, 9, "✅ Подтверждено")
            break

    await callback.message.answer("✅ Вы подтвердили участие в Киноигре!")
    await callback.answer()


@router.callback_query(F.data == "game_confirm_no")
async def cancel_game(callback: CallbackQuery):
    user_id = callback.from_user.id
    rows = game_sheet.get_all_records()

    for i, row in enumerate(rows, start=2):
        if str(row.get("user_id")) == str(user_id):
            game_sheet.update_cell(i, 9, "❌ Отменено")
            break

    await callback.message.answer("❌ Вы отменили участие в киноигре.")
    await callback.answer()


# ЦЕПОЧКА КЛАВИШ КИНОВЕЧЕРА




def get_1movie_inline_keyboard():
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Назад", callback_data="info_start")],
            [InlineKeyboardButton(text="Доступные мероприятия", callback_data="available_movie")],
            [InlineKeyboardButton(text="Правила на Киновечере", callback_data="movie_rules")]
        ]
    )
    return keyboard


def get_2movie_inline_keyboard():
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Назад", callback_data="info_start")],
            [InlineKeyboardButton(text="Зарегистироваться", callback_data="reg_movie")]
        ]
    )
    return keyboard


@router.callback_query(F.data == "available_movie")
async def check_quiz_availability(callback: CallbackQuery):
    events = events_sheet.get_all_records()
    movie = next((e for e in events if e["Название"] == "Киновечер"), None)

    if movie and movie["Доступно"].lower() == "да":
        date = movie["Дата_начало"]
        time = movie["Время"]
        place = movie["Место"]
        await callback.message.answer(
            f"📅 Киновечер состоится {date} в {time} в {place}.\n\n Регистрация открыта!",
            reply_markup=get_2movie_inline_keyboard()
        )
    else:
        await callback.message.answer("❌ Регистрация на Киновечер пока недоступна.",
                                      reply_markup=back_to_the_start())
    await callback.message.delete()


def agree_movie_keyboard():
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Согласен(-на)", callback_data="movie_FSM")]
        ]
    )
    return keyboard


@router.callback_query(F.data == "reg_movie")
async def law_movie_registration(callback: CallbackQuery):
    await callback.message.delete()
    await callback.message.answer("Перед началом — секунда формальности.\n\n"
                                  "Нам нужно твоё <b>согласие</b> на обработку персональных данных"
                                  " в соответствии с Федеральным законом от 27.07.2006 №152-ФЗ"
                                  " «О персональных данных». ",
                                  parse_mode="HTML",
                                  reply_markup=agree_movie_keyboard())
    await callback.answer()


@router.callback_query(F.data == "movie_FSM")
async def start_movie_registration(callback: CallbackQuery, state: FSMContext):
    await callback.message.delete()
    await state.update_data(movie_approval="да")
    await callback.message.answer("Являешься ли ты студентом(-кой) МГТУ им. Н.Э. Баумана?\n\n"
                                  "<i>Ответь 'да' или 'нет'.</i>",
                                  parse_mode='HTML')
    await state.set_state(MovieRegistration.movie_bauman)
    await callback.answer()


@router.message(MovieRegistration.movie_bauman)
async def check_student_status_movie(message: Message, state: FSMContext):
    text = message.text.strip().lower()

    if text not in ["да", "нет"]:
        await message.answer("❌ <b>Пожалуйста, ответьте только 'да' или 'нет'.</b>",
                             parse_mode='HTML')
        return

    await state.update_data(movie_bauman=text)
    await message.answer("<b>Твои имя и фамилия?</b>\n\n"
                         "<i>Если ты попал(-а) не туда, то в конце будет кнопка 'Отменить'"
                         " и ты вернешься в начало.</i>",
                         parse_mode="HTML")
    await state.set_state(MovieRegistration.movie_name)


@router.message(MovieRegistration.movie_name)
async def get_movie_group(message: Message, state: FSMContext):
    await state.update_data(movie_name=message.text)
    await message.answer("Номер твоей группы обучения:\n\n<i>(Например:РК5-11Б)</i>", parse_mode="HTML")
    await state.set_state(MovieRegistration.movie_group_number)


@router.message(MovieRegistration.movie_group_number)
async def get_movie_sum(message: Message, state: FSMContext):
    await state.update_data(movie_group_number=message.text)
    data = await state.get_data()
    movie_username = message.from_user.username
    movie_user_mention = f"@{movie_username}" if movie_username else "без username"

    summary = (
        f"📝 Вот твои данные:\n\n"
        f"🎓 Являюсь студентом(-кой) МГТУ: {data['movie_bauman']}\n"
        f"👤 Имя и фамилия: {data['movie_name']} ({movie_user_mention})\n"
        f"🏷 Номер группы: {data['movie_group_number']}"
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Начать заново", callback_data="movie_restart")],
            [InlineKeyboardButton(text="Подтвердить", callback_data="movie_confirm")],
            [InlineKeyboardButton(text="Отмена", callback_data="denied")]
        ]
    )

    await message.answer(summary, reply_markup=keyboard)
    await state.set_state(MovieRegistration.movie_confirm)


@router.callback_query(F.data == "movie_confirm")
async def confirm_movie_registration(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    await callback.message.delete()

    events = events_sheet.get_all_records()
    movie = next((e for e in events if e["Название"] == "Киновечер"), None)
    group_link = movie["Ссылка на группу"]
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Перейти в группу 🎬", url=group_link)],
            [InlineKeyboardButton(text="Назад!", callback_data="start")]
        ]
    )

    await callback.message.answer("✅ Регистрация завершена! <b>Увидимся на Киновечере!</b> 🎉\n\n "
                                  "Переходи в группу, чтобы быть в курсе всей информации по мероприятию!👇",
                                  reply_markup=keyboard,
                                  parse_mode='HTML')
    username = callback.from_user.username or "без username"
    movie_timestamp = datetime.now().strftime("%d.%m.%Y %H:%M")

    row = [str(data['movie_name']),
           str(data['movie_group_number']),
           f"@{username}",
           movie_timestamp,
           str(callback.from_user.id),
           str(data['movie_bauman']),
           str(data['game_approval'])]

    print("Row:", row)
    print("Sheet:", movie_sheet)
    print("FSM data:", data)

    try:
        movie_sheet.append_row(row)
    except Exception as e:
        await callback.message.answer(f"Ошибка при записи в таблицу: {e}")

    await callback.message.delete()
    await state.clear()
    await callback.answer()


@router.callback_query(F.data == "movie_restart")
async def law_movie_registration(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.delete()
    await callback.message.answer("Хорошо, давай начнём заново\n\n"
                                  "И снова формальность.\n"
                                  "Нам нужно твоё <b>согласие</b> на обработку персональных данных"
                                  " в соответствии с Федеральным законом от 27.07.2006 №152-ФЗ"
                                  " «О персональных данных». ",
                                  parse_mode="HTML",
                                  reply_markup=agree_movie_keyboard())
    await callback.answer()


@router.message(F.text == "/notify_movie")
async def notify_movie(message: Message):
    events = events_sheet.get_all_records()

    movie = next((e for e in events if e["Название"] == "Киновечер"), None)
    if not movie or movie["Доступно"].lower() != "да":
        await message.answer("❌ Киновечер недоступен для рассылки.")
        return
    # remember = movie["Не забудьте"]
    date = movie["Дата_начало"]
    time = movie["Время"]
    group_link = movie["Ссылка на группу"]

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Перейти в группу 🎬", url=group_link)]
        ]
    )

    rows = movie_sheet.get_all_records()
    sent_count = 0

    for row in rows:
        user_id = row.get("user_id")
        if user_id:
            try:
                await bot.send_message(
                    user_id,
                    f"🎬 Напоминаем: <b>Киновечер</b> состоится {date} в {time}!\n"
                    f"Присоединяйтесь к группе, если ещё нет, вся информация там! 👇\n\n"
                    f"<b>P.S. Не забудьте свои карты для прохода в университет</b>",
                    reply_markup=keyboard,
                    parse_mode="HTML"
                )
                sent_count += 1
                await asyncio.sleep(0.5)
            except Exception as e:
                print(f"Не удалось отправить {user_id}: {e}")
    await message.answer(f"✅ Рассылка завершена. Уведомлений отправлено: {sent_count}")


# ЦЕПОЧКА КЛАВИШ ВЫЕЗДА




def get_1trip_inline_keyboard():
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Назад", callback_data="info_start")],
            [InlineKeyboardButton(text="Доступные мероприятия", callback_data="available_trip")]
        ]
    )
    return keyboard


def get_2trip_inline_keyboard():
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Назад", callback_data="info_start")],
            [InlineKeyboardButton(text="Зарегистироваться", callback_data="reg_trip")]
        ]
    )
    return keyboard


@router.callback_query(F.data == "available_trip")
async def check_trip_availability(callback: CallbackQuery):
    events = events_sheet.get_all_records()
    trip = next((e for e in events if e["Название"] == "Выезд"), None)
    if trip and trip["Доступно"].lower() == "да":

        date_trip_start = trip["Дата_начало"]
        date_trip_finish = trip["Дата_конец"]
        time = trip["Время"]
        place = trip["Место"]

        await callback.message.answer(
            f"📅 Выезд состоится с {date_trip_start} по {date_trip_finish}. Сбор на выезд будет в {time}, из {place}."
            f"\n\n Регистрация открыта!",
            reply_markup=get_2trip_inline_keyboard()
        )
    else:
        await callback.message.answer("❌ Регистрация на Выезд пока недоступна.",
                                      reply_markup=back_to_the_start())
    await callback.message.delete()


def agree_trip_keyboard():
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Согласен(-на)", callback_data="trip_FSM")]
        ]
    )
    return keyboard


@router.callback_query(F.data == "reg_trip")
async def law_trip_registration(callback: CallbackQuery):
    await callback.message.delete()
    await callback.message.answer("Перед началом — секунда формальности.\n\n"
                                  "Нам нужно твоё <b>согласие</b> на обработку персональных данных"
                                  " в соответствии с Федеральным законом от 27.07.2006 №152-ФЗ"
                                  " «О персональных данных». ",
                                  parse_mode="HTML",
                                  reply_markup=agree_trip_keyboard())
    await callback.answer()


@router.callback_query(F.data == "trip_FSM")
async def start_trip_registration(callback: CallbackQuery, state: FSMContext):
    await callback.message.delete()
    await state.update_data(trip_approval="да")
    await callback.message.answer("Являешься ли ты студентом(-кой) МГТУ им. Н.Э. Баумана?\n\n"
                                  "<i>Ответь 'да' или 'нет'.</i>",
                                  parse_mode='HTML')
    await state.set_state(TripRegistration.trip_bauman)
    await callback.answer()



@router.message(TripRegistration.trip_bauman)
async def check_student_status_trip(message: Message, state: FSMContext):
    text = message.text.strip().lower()

    if text not in ["да", "нет"]:
        await message.answer("❌ Пожалуйста, ответьте только 'да' или 'нет'.")
        return

    if text == "нет":
        # остановка регистрации
        await message.answer(
            "❌ Регистрация доступна только для студентов МГТУ.\n\n"
            "Вы можете вернуться в начало и выбрать другое действие:",
            reply_markup=back_to_the_start()
        )
        await state.clear()
        return

    await state.update_data(trip_bauman=text)
    await message.answer("<b>Твоё имя и фамилия?</b>\n\n"
                         "<i>Если ты попал не туда, то в конце будет кнопка 'Отменить'"
                         " и ты вернешься в начало.</i>",
                         parse_mode="HTML")
    await state.set_state(TripRegistration.trip_name)


@router.message(TripRegistration.trip_name)
async def get_trip_group(message: Message, state: FSMContext):
    await state.update_data(trip_name=message.text)
    await message.answer("Номер твоей группы обучения:\n\n<i>(Например:РК5-11Б)</i>",
                         parse_mode="HTML")
    await state.set_state(TripRegistration.trip_group_number)


@router.message(TripRegistration.trip_group_number)
async def get_trip_phone(message: Message, state: FSMContext):
    await state.update_data(trip_group_number=message.text)
    await message.answer("Номер твоего телефона:\n\n<i>(Например:+79061234567)</i>",
                         parse_mode="HTML")
    await state.set_state(TripRegistration.trip_phone_number)


@router.message(TripRegistration.trip_phone_number)
async def get_trip_bday(message: Message, state: FSMContext):
    await state.update_data(trip_phone_number=message.text)
    await message.answer("Твоя дата рождения:\n\n<i>(Например: 23.05.2005)</i>",
                         parse_mode="HTML")
    await state.set_state(TripRegistration.trip_date_of_birth)


@router.message(TripRegistration.trip_date_of_birth)
async def get_trip_illness(message: Message, state: FSMContext):
    await state.update_data(trip_date_of_birth=message.text)
    await message.answer("Есть ли у тебя аллергия/болезни/травмы?\n\n<i>(Если нет, то пиши '-':)</i>",
                         parse_mode="HTML")
    await state.set_state(TripRegistration.trip_illness)


@router.message(TripRegistration.trip_illness)
async def get_trip_food(message: Message, state: FSMContext):
    await state.update_data(trip_illness=message.text)
    await message.answer("Есть ли у тебя особенности по питанию?\n\n"
                         "<i>(Примеры ответов: Ем всё/Не ем мясо. Если что-то иное — пиши)</i>",
                         parse_mode="HTML")
    await state.set_state(TripRegistration.trip_special)


@router.message(TripRegistration.trip_special)
async def get_trip_sum(message: Message, state: FSMContext):
    await state.update_data(trip_special=message.text)
    data = await state.get_data()
    trip_username = message.from_user.username
    trip_user_mention = f"@{trip_username}" if trip_username else "без username"

    summary = (
        f"📝 Вот твои данные:\n\n"
        f"🎓 Являюсь студентом(-кой) МГТУ: {data['trip_bauman']}\n"
        f"👤 Имя и фамилия: {data['trip_name']} ({trip_user_mention})\n"
        f" Номер телефона: {data['trip_phone_number']}\n"
        f"🏷 Номер группы: {data['trip_group_number']}\n"
        f" Дата рождения: {data['trip_date_of_birth']}\n"
        f" Аллергия/болезни/травмы: {data['trip_illness']}\n"
        f" Особенности питания: {data['trip_special']}"
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Начать заново", callback_data="trip_restart")],
            [InlineKeyboardButton(text="Подтвердить", callback_data="trip_confirm")],
            [InlineKeyboardButton(text="Отмена", callback_data="denied")]
        ]
    )

    await message.answer(summary, reply_markup=keyboard)
    await state.set_state(TripRegistration.trip_confirm)


@router.callback_query(F.data == "trip_confirm")
async def confirm_registration(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    user_id = callback.from_user.id
    event = get_event_by_name("Выезд")
    if not event:
        await callback.message.answer("Ошибка: событие не найдено.",
                                      reply_markup=back_to_the_start())
        return
    if is_user_registered(trip_sheet, user_id):
        await callback.message.delete()
        await callback.message.answer("Вы уже зарегистрированы в основном списке.",
                                      reply_markup=back_to_the_start())
        return
    await callback.answer()

    if is_user_registered(trip_sheet2, user_id):
        await callback.message.delete()
        await callback.message.answer("Вы уже находитесь в листе ожидания.",
                                      reply_markup=back_to_the_start())
        return
    await callback.answer()

    main_records = trip_sheet.get_all_records()
    count = len(main_records)
    limit = int(event["Лимит"])
    username = callback.from_user.username or "без username"
    trip_timestamp = datetime.now().strftime("%d.%m.%Y %H:%M")

    row = [
        str(data['trip_name']),
        str(data['trip_group_number']),
        f"@{username}",
        trip_timestamp,
        user_id,
        str(data['trip_phone_number']),
        str(data['trip_date_of_birth']),
        str(data['trip_illness']),
        str(data['trip_special']),
        str(data['trip_bauman']),
        str(data['trip_approval'])
    ]

    group_link = event["Ссылка на группу"]
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Перейти в группу", url=group_link)],
            [InlineKeyboardButton(text="Назад!", callback_data="start")]
        ]
    )

    if count < limit:
        append_row(trip_sheet, row)
        await callback.message.delete()
        await callback.message.answer("✅ Регистрация завершена! <b>Увидимся на Выезде!</b> 🎉\n\n"
                                      "Переходи в группу, чтобы быть в курсе всей информации по выезду!👇",
                                      reply_markup=keyboard,
                                      parse_mode='HTML')
        await state.clear()
        await callback.answer()
    else:
        # лист ожидания
        append_row(trip_sheet2, row)
        await callback.message.delete()
        await callback.message.answer(
            "⚠️ Основные места заняты.\n"
            "Вы зарегистрированы, но добавлены в <b>лист ожидания</b>.\n\n"
            "<b>Не спешите расстраиваться!</b>\n\n"
            "После закрытия регистрации мы начнём собирать подтверждения, "
            "как правило, некоторые участники отказываются от поездки, в таком случае мы свяжемся с Вами "
            "и если Вы будете согласны, то займёте их место\n\n"
            "Благодарим за понимание!🙏",
            parse_mode="HTML",
            reply_markup=back_to_the_start()
        )
        await state.clear()
        await callback.answer()

    # @router.callback_query(F.data == "trip_confirm")
    # async def confirm_registration(callback: CallbackQuery, state: FSMContext):
    #     data = await state.get_data()
    # events = events_sheet.get_all_records()
    # trip = next((e for e in events if e["Название"] == "Выезд"), None)
    # group_link = trip["Ссылка на группу"]
    # keyboard = InlineKeyboardMarkup(
    #     inline_keyboard=[
    #         [InlineKeyboardButton(text="Перейти в группу", url=group_link)],
    #         [InlineKeyboardButton(text="Назад!", callback_data="start")]
    #     ]
    # )
    # await callback.message.delete()
    # await callback.message.answer("✅ Регистрация завершена! <b>Увидимся на Выезде!</b> 🎉\n\n"
    #                               "Переходи в группу, чтобы быть в курсе всей информации по выезду!👇",
    #                               reply_markup=keyboard,
    #                               parse_mode='HTML')
    # username = callback.from_user.username or "без username"
    # trip_timestamp = datetime.now().strftime("%d.%m.%Y %H:%M")
    #
    # row = [str(data['trip_name']),
    #        str(data['trip_group_number']),
    #        f"@{username}",
    #        trip_timestamp,
    #        user_id,
    #        str(data['trip_phone_number']),
    #        str(data['trip_date_of_birth']),
    #        str(data['trip_illness']),
    #        str(data['trip_special']),
    #        str(data['trip_bauman']),
    #        str(data['trip_approval'])]
    #
    # print("Row:", row)
    # print("Sheet:", trip_sheet)
    # print("FSM data:", data)
    #
    # try:
    #     trip_sheet.append_row(row)
    # except Exception as e:
    #     await callback.message.answer(f"Ошибка при записи в таблицу: {e}")
    #
    # await callback.message.delete()
    # await state.clear()
    # await callback.answer()


@router.callback_query(F.data == "trip_restart")
async def law_trip_registration(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.delete()
    await callback.message.answer("Хорошо, давай начнём заново\n\n"
                                  "И снова формальность.\n"
                                  "Нам нужно твоё <b>согласие</b> на обработку персональных данных"
                                  " в соответствии с Федеральным законом от 27.07.2006 №152-ФЗ"
                                  " «О персональных данных». ",
                                  parse_mode="HTML",
                                  reply_markup=agree_trip_keyboard())
    await callback.answer()


@router.message(F.text == "/notify_trip")
async def notify_trip(message: Message):
    events = events_sheet.get_all_records()

    trip = next((e for e in events if e["Название"] == "Выезд"), None)
    if not trip or trip["Доступно"].lower() != "да":
        await message.answer("❌ Выезд недоступен для рассылки.")
        return

    date_start = trip["Дата_начало"]
    date_finish = trip["Дата_конец"]
    time = trip["Время"]
    group_link = trip["Ссылка на группу"]
    place = trip["Место"]

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Перейти в группу 🎬", url=group_link)]
        ]
    )

    rows = trip_sheet.get_all_records()
    sent_count = 0

    for row in rows:
        user_id = row.get("user_id")
        if user_id:
            try:
                await bot.send_message(
                    user_id,
                    f"🎬 Напоминаем: Выезд состоится с {date_start} по {date_finish}, сбор в {time} в {place}!\n"
                    f"Присоединяйтесь к группе, если ещё нет, далее вся информация будет там! 👇",
                    reply_markup=keyboard
                )
                sent_count += 1
                await asyncio.sleep(0.5)
            except Exception as e:
                print(f"Не удалось отправить {user_id}: {e}")
    await message.answer(f"✅ Рассылка завершена. Уведомлений отправлено: {sent_count}")


# Общие клавиши и сообщения




@router.callback_query(lambda c: c.data == "info_more")
async def process_more_info(callback: CallbackQuery):
    await callback.message.answer("Вот тебе более подробная информация")
    await callback.answer()


@router.callback_query(lambda c: c.data == "info_game")
async def process_more_info(callback: CallbackQuery):
    # await callback.message.delete()
    await callback.message.answer(
        "Киноигра — командный квиз с вопросами по всему, что связано с кино и сериалами!"
        "\n\nКоманды от 4 до 8 человек\n\nВеселимся, отдыхаем, получаем подарки\n\n"
        "<b>Нажимай на кнопку ниже чтобы узнать правила.</b>"
        "\n\nP.S. Усердно думаем над рейтингом команд)",
        reply_markup=get_1game_inline_keyboard(),
        parse_mode="HTML")
    await callback.message.delete()
    await callback.answer()


@router.callback_query(lambda c: c.data == "game_rules")
async def process_more_info(callback: CallbackQuery):
    # await callback.message.delete()
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Назад", callback_data="info_game")]
        ]
    )
    await callback.message.answer(
        "Вот основные правила Киноигр:\n\n"
        "1️⃣Ключевым правилом является — честность. "
        "За нарушение этого правила: в первый раз делаем предупреждение, "
        "за дальнейшие подобные действия член команды или вся команда могут быть дисквалифицированы.\n"
        "Что является нарушением? Звонок другу, смс чат-боту, ну и очевидно, поиск ответа в интернете.\n\n"
        "2️⃣Чистота и порядок.\n"
        "Пожалуйста, не мусорьте. Убедитесь, что после окончания мероприятия всё выброшено в урны.\n\n"
        "3️⃣Бережное отношение к имуществу.\n"
        "Просьба не крушить и не ломать ничего в помещении. Давайте уважать пространство, в котором находимся.\n\n"
        "4️⃣Берите с собой шариковую ручку\n\n"
        "5️⃣Берите с собой хорошее настроение.\n"
        "Что входит в хорошее настроение? Приколы и позитив, желание хорошо провести время.\n\n"
        "Спасибо за понимание 💌",
        reply_markup=keyboard,
        parse_mode="HTML")
    await callback.message.delete()
    await callback.answer()


@router.callback_query(lambda c: c.data == "info_movie")
async def process_more_info(callback: CallbackQuery):
    await callback.message.answer("Киновечер — смотрим кино на больших экранах прямо в Бауманке.\n"
                                  "Зови своих друзей и подруг на наши уютные вечера с угощениями — "
                                  "проведём время отлично!\n\n"
                                  "<b>Нажимай на кнопку ниже чтобы узнать правила.</b>",
                                  reply_markup=get_1movie_inline_keyboard(),
                                  parse_mode="HTML")
    await callback.message.delete()
    await callback.answer()


@router.callback_query(lambda c: c.data == "movie_rules")
async def process_more_info(callback: CallbackQuery):
    # await callback.message.delete()
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Назад", callback_data="info_movie")]
        ]
    )
    await callback.message.answer(
        "Вот основные правила Киновечера:\n\n"
        "1️⃣Не заказывать доставку.\n"
        "Во избежание лишнего движения и отвлечения участников, пожалуйста, не заказывайте еду или напитки. "
        "Но вы можете принести с собой свои вкусняшки!\n\n"
        "2️⃣Чистота и порядок.\n"
        "Пожалуйста, не мусорьте. Убедитесь, что после окончания мероприятия всё выброшено в урны.\n\n"
        "3️⃣Бережное отношение к имуществу.\n"
        "Просьба не крушить и не ломать ничего в помещении. Давайте уважать пространство, в котором находимся.\n\n"
        "4️⃣Берите с собой хорошее настроение.\n"
        "Что входит в хорошее настроение? Приколы и позитив, желание хорошо провести время.\n\n"
        "5️⃣<b>Не забудьте с собой карты для прохода в университет!</b>\n\n"
        "Спасибо за понимание 💌",
        reply_markup=keyboard,
        parse_mode="HTML")
    await callback.message.delete()
    await callback.answer()


@router.callback_query(lambda c: c.data == "info_trip")
async def process_more_info(callback: CallbackQuery):
    await callback.message.answer("Выезд — наши самые крупные и запоминающиеся мероприятия."
                                  "Проходят они в лагере 'Бауманец' в Ступино. "
                                  "Развлечения, питание и незабываемые впечатления"
                                  "\n\nТолько раз в семестр.\n\nУспей попасть!",
                                  reply_markup=get_1trip_inline_keyboard())
    await callback.message.delete()
    await callback.answer()


def get_real_main_inline_keyboard():
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Киноигра", callback_data="info_game")],
            [InlineKeyboardButton(text="Киновечер", callback_data="info_movie")],
            [InlineKeyboardButton(text="Выезд", callback_data="info_trip")],
            [InlineKeyboardButton(text="Мои активные регистрации", callback_data="my_regs")]
        ]
    )
    return keyboard


@router.callback_query(F.data == "my_regs")
async def show_my_regs(callback: CallbackQuery):
    user_id = str(callback.from_user.id)
    active_regs = []
    events = events_sheet.get_all_records()
    sheets_to_check = [
        ("Киновечер", movie_sheet),
        ("Киноигра", game_sheet),
        ("Киноигра", game_sheet2),
        ("Выезд", trip_sheet),
        ("Выезд", trip_sheet2)
    ]

    for name, sheet in sheets_to_check:
        rows = sheet.get_all_records()
        for row in rows:
            if str(row.get("user_id")) == user_id:
                event_info = next((e for e in events if e["Название"] == name), None)
                if event_info:
                    date = event_info.get("Дата_начало", "—")
                    time = event_info.get("Время", "—")
                    group_link = event_info.get("Ссылка на группу", "").strip()
                    line = f"• {name} — {date} в {time}"  # скелет строки
                    if group_link:
                        line += f" — <a href=\"{group_link}\">Группа по мероприятию</a>"
                    active_regs.append(line)
                else:
                    active_regs.append(f"• {name} — дата/время не указаны")
                break

    if active_regs:
        events_list = "\n\n".join(active_regs)
        await callback.message.answer(
            f"📋 Ваши активные регистрации:\n\n{events_list}",
            parse_mode="HTML"
        )
    else:
        await callback.message.answer("❌ У вас пока нет активных регистраций.")
    await callback.answer()


@router.message(Command("notify_missing_username"))
async def notify_missing_username(message: Message):
    records = game_sheet.get_all_records()
    count = 0
    failed = 0
    contact_keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text="Написать организатору",
                url="https://t.me/planb_on_fire"
            )]
        ]
    )
    for row in records:
        user_id = row.get("user_id")
        tg = row.get("Тг")
        # проверяем отсутствие юзернейма
        if tg and tg.strip().lower() in ["@без username", "без username"]:
            try:
                await message.bot.send_message(
                    user_id,
                    "Привет! 👋\n\n"
                    "При регистрации у тебя не был указан @ username (Имя пользователя).\n"
                    "Чтобы мы могли связаться с тобой, пожалуйста, добавь его у себя в настройках Телеграма "
                    "и напиши свой username организатору. "
                    "Чтобы открыть чат с ним, нажми на кнопку:",
                    reply_markup=contact_keyboard
                )
                count += 1
            except Exception as e:
                print(f"Не удалось отправить сообщение пользователю {user_id}: {e}")
                failed += 1
    await message.answer(
        f"Готово!\n"
        f"Отправлено сообщений: {count}\n"
        f"Не удалось отправить: {failed}"
    )


@router.callback_query(F.data == "denied")
async def denied_registration(callback: CallbackQuery, state: FSMContext):
    await callback.message.delete()
    await callback.message.answer("❌ Регистрация отменена! Подумаем еще раз?",
                                  reply_markup=back_to_the_start())
    await state.clear()
    await callback.answer()


async def send_start_message(target):
    await target.answer(
        text="Привет!\n\nЯ бот для регистрации на мероприятия Бауманского киноклуба <b>'Киношки'</b> "
             "\n\nНиже есть кнопки для выбора интересующего тебя мероприятия, жми!"
             "\n\nТам же будут ответы на некоторые вопросы и правила."
             "\n\nЧтобы вернуться к этому сообщению пиши /start",
        parse_mode="HTML",
        reply_markup=get_real_main_inline_keyboard()
    )


def back_to_the_start():
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="К началу!", callback_data="start")]
        ]
    )
    return keyboard


@router.message(Command("start"))
async def agree_start(message: Message):
    await send_start_message(message)


@router.callback_query(F.data.in_(["start", "info_start"]))
async def agree_callback(callback: CallbackQuery):
    # await callback.message.delete()
    await send_start_message(callback.message)
    await callback.message.delete()
    await callback.answer()


@router.message()
async def mess(message: Message):
    await message.answer("Не пиши мне такое!\nИли что-то пошло не так?\n\nТогда жми /start")



# @router.message(Command("about"))
# async def about(message: Message):
#     await message.answer(f"Нуу, вот тебе твоё имя\nТвое имя:\n{message.from_user.full_name}",
#                          reply_markup=get_main_inline_keyboard())

# def get_main_inline_keyboard():
#     keyboard = InlineKeyboardMarkup(
#         inline_keyboard=[
#             [InlineKeyboardButton(text="Открыть сайт", url="https://ru.wikipedia.org")],
#             [InlineKeyboardButton(text="Подробнее", callback_data="info_more")]
#         ]
#     )
#     return keyboard


# async def send_agree_message(target):
#     await target.answer(
#         text="Для того чтобы принять участие в наших мероприятиях,"
#              " необходимо твоё <b>согласие на обработку персональных данных</b>",
#         parse_mode="HTML",
#         reply_markup=agree_keyboard()
#     )

#
#
# @router.message(Command("start"))
# @router.message(F.text.lower() == "старт")
# async def start_message(message: Message):
#     await send_start_message(message)


#   ReplyKeyboardMarkup,
#   KeyboardButton,

# @router.message(Command("help"))
# @router.message(F.text.lower() =="помощь")
# async def help(message:Message):
#     await message.answer("Команды: \n\n/start - запустить бота\n/help - список команд\n/about - имя пользователя",
#                          reply_markup=get_main_reply_keyboard())

# @router.message(Command("start"))
# @router.message(F.text.lower() =="старт")
# @router.callback_query(F.data.in_(["info_start"]))
# async def start(message: Message):
#     await message.answer(
#        "Привет!\n\nЯ бот для регистрации на мероприятия <b>Киношек</b>
#        \n\nНиже есть кнопки для выбора интересующего тебя мероприятия, жми!\n\nЕсли что-то пошло не так, пиши /help",
#         parse_mode="HTML",
#         reply_markup=get_real_main_inline_keyboard())
# а вот тебе<a href='https://google.com'> гугл</a>
# Привет!\n\nЯ <b>будущий</b> бот <i>для реги на мероприятия киношек</i> \n\n, если забыл)\n\nНапиши /help для помощи
# url="https://ru.wikipedia.org"
# Отправление ссылок на аддоны
# @dp.callback_query(F.data.in_(telegraphLinks))
# async def send_addon1(callback: types.CallbackQuery):
#    await callback.message.answer(telegraphLinks[callback.data])
