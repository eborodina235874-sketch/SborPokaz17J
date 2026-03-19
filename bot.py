import os
import pandas as pd
from datetime import datetime
from umaxbot import Bot, Dispatcher, types
from umaxbot.fsm import State, StatesGroup, FSMContext

TOKEN = "f9LHodD0cOLppXCKzWiAHSfTq-lgD881ak2ktA96D8sGuWkLjwQpwbxsIXfN5vIT77T04dOmohcoqynHQSUR"
EXCEL_FILE = "pokazaniya.xlsx"

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

class MeterStates(StatesGroup):
    waiting_for_flat = State()
    waiting_for_cold = State()
    waiting_for_hot = State()
    waiting_for_gas = State()
    waiting_for_electro = State()
    waiting_for_confirmation = State()

def save_to_excel(data):
    new_row = pd.DataFrame([data])
    if os.path.exists(EXCEL_FILE):
        df = pd.read_excel(EXCEL_FILE, engine='openpyxl')
        df = pd.concat([df, new_row], ignore_index=True)
    else:
        df = new_row
    df.to_excel(EXCEL_FILE, index=False, engine='openpyxl')

@dp.message_handler(commands=['start'])
async def cmd_start(message: types.Message):
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(types.KeyboardButton("Start"))
    await message.reply(
        "Добрый день!\nЗапишите текущие показания счетчиков.\nНажмите кнопку Start для начала.",
        reply_markup=keyboard
    )

@dp.message_handler(lambda message: message.text == "Start")
async def process_start(message: types.Message, state: FSMContext):
    await state.update_data(date=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    await MeterStates.waiting_for_flat.set()
    await message.reply("Введите номер квартиры:", reply_markup=types.ReplyKeyboardRemove())

@dp.message_handler(state=MeterStates.waiting_for_flat)
async def process_flat(message: types.Message, state: FSMContext):
    if not message.text.strip().isdigit():
        await message.reply("Пожалуйста, введите номер квартиры цифрами.")
        return
    await state.update_data(flat=message.text.strip())
    await MeterStates.waiting_for_cold.set()
    await message.reply("Введите показания холодной воды (только цифры):")

@dp.message_handler(state=MeterStates.waiting_for_cold)
async def process_cold(message: types.Message, state: FSMContext):
    val = message.text.strip().replace('.', '', 1)
    if not val.isdigit():
        await message.reply("Введите число (можно десятичное через точку).")
        return
    await state.update_data(cold=message.text.strip())
    await MeterStates.waiting_for_hot.set()
    await message.reply("Введите показания горячей воды:")

@dp.message_handler(state=MeterStates.waiting_for_hot)
async def process_hot(message: types.Message, state: FSMContext):
    val = message.text.strip().replace('.', '', 1)
    if not val.isdigit():
        await message.reply("Введите число.")
        return
    await state.update_data(hot=message.text.strip())
    await MeterStates.waiting_for_gas.set()
    await message.reply("Введите показания газа:")

@dp.message_handler(state=MeterStates.waiting_for_gas)
async def process_gas(message: types.Message, state: FSMContext):
    val = message.text.strip().replace('.', '', 1)
    if not val.isdigit():
        await message.reply("Введите число.")
        return
    await state.update_data(gas=message.text.strip())
    await MeterStates.waiting_for_electro.set()
    await message.reply(
        "Введите показания электроэнергии.\n"
        "Если у вас многотарифный счётчик, введите значения через запятую или пробел (например: 123, 456 или 123 456):"
    )

@dp.message_handler(state=MeterStates.waiting_for_electro)
async def process_electro(message: types.Message, state: FSMContext):
    await state.update_data(electro=message.text.strip())
    data = await state.get_data()
    summary = (
        f"Проверьте введённые показания:\n"
        f"Номер квартиры: {data['flat']}\n"
        f"Холодная вода: {data['cold']}\n"
        f"Горячая вода: {data['hot']}\n"
        f"Газ: {data['gas']}\n"
        f"Электроэнергия: {data['electro']}\n\n"
        "Всё верно?"
    )
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(types.KeyboardButton("Подтвердить"), types.KeyboardButton("Вернуться в начало"))
    await MeterStates.waiting_for_confirmation.set()
    await message.reply(summary, reply_markup=keyboard)

@dp.message_handler(state=MeterStates.waiting_for_confirmation, text="Подтвердить")
async def process_confirm(message: types.Message, state: FSMContext):
    data = await state.get_data()
    save_to_excel({
        'date': data['date'],
        'flat': data['flat'],
        'cold': data['cold'],
        'hot': data['hot'],
        'gas': data['gas'],
        'electro': data['electro']
    })
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(types.KeyboardButton("Start"))
    await message.reply(
        "Ваши показания успешно переданы!\nХотите передать новые показания? Нажмите Start.",
        reply_markup=keyboard
    )
    await state.finish()

@dp.message_handler(state=MeterStates.waiting_for_confirmation, text="Вернуться в начало")
async def process_cancel(message: types.Message, state: FSMContext):
    await state.finish()
    await cmd_start(message)

if __name__ == '__main__':
    print("Бот запущен...")
    dp.start_polling()
