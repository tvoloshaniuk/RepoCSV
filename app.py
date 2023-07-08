from flask import Flask, render_template, request
import pandas as pd
import chardet
import pygal

# Программа по валидации csv таблицы и отрисовке нужных данных (по варианту) на графике
app = Flask(__name__)

#путь к стандартному файлу для примера
defaultTablePath = 'static/exampleTable.csv'
#путь, по которому будет сохраняться и пеоесохраняться с заменой успешный файл пользователя
uploadedFilePath = 'static/uploadedTable.csv'
# Последняя удачная таблица. Чтобы если ошибка, всегда было что нарисовать (в формате line_chart.render_data_uri() )
lastSuccessfulTable = None

expected_tableTitles = ['Horsepower', 'Weight', 'Origin']
origin_AllowedValues = ['US', 'Europe', 'Japan']
expected_tableTitles_Datatypes = {
    'Horsepower': float,
    'Weight': float,
    'Origin': str
}
# названия осей на графике
graphTitleY = expected_tableTitles[0]   # ось Y
graphTitleX = expected_tableTitles[1]   # ось X

# Вспомогательный метод, который определяет кодировку файла (понадобится в алгоритме)
def defineEncoding(tablePath):
    with open(tablePath, 'rb') as file:
        result = chardet.detect(file.read())
        encoding = result['encoding']
        return encoding

# Проверка подходит ли таблица ожиданиям.
# При этом допукскается, если какие-то ячейки будут пустыми (их значение будет Nan - так действует astype())
def validateTable(table):
    if not isinstance(table, pd.DataFrame):
        return False, "Валидация таблицы не пройдена: pandas lib не распознал файл как .csv"

    if not all(name in table.columns for name in expected_tableTitles):
        return False, "Валидация таблицы не пройдена: не найден минимум 1 требуемый заголовок"

    for key, value in expected_tableTitles_Datatypes.items():
        if key in table.columns:
             try:
                 # попытка привести каждый нужный столбец dataFrame к нужному типу
                table[key] = table[key].str.strip().astype(value)    #strip() - обрезать пробелы после значения и перед ним
             except:
                incorrect_cells = table[key][pd.to_numeric(table[key], errors='coerce').isna()]
                return False, f"Столбец '{key}' содержит неправильные значения в ячейках: {incorrect_cells}"

             if key == 'Origin':
                 incorrect_values = table.loc[~table['Origin'].isin(origin_AllowedValues) & table['Origin'].notna(), 'Origin']
                 if not incorrect_values.empty:
                     return False, f"Столбец {key} содержит неправильные значения: {incorrect_values.unique()}"
        else:
            return False, "Ошибка при валидация таблицы: в словаре ожидаемых заголовков был такой ключ, которого нет в заголовках dataFrame "

    return True


# Принимает на вход путь к csv файлу, на его основе создает DataFrame (pandas lib), но удаляя строку index=1
# Возвращает таблицу в формате DataFrame, или -- False, {причина ошибки} (если валидация таблицы прошла не успешно)
def csvToDataFrame(filePath):
    csvTable_DataFrame = pd.read_csv(filePath, sep=';', encoding=defineEncoding(filePath))
    csvTable_DataFrame = csvTable_DataFrame.drop(0).reset_index(drop=True)  # удаление по индексу 0 ряда таблицы (название столбца не являетя рядом в dataFrame)
    validationResult = validateTable(csvTable_DataFrame) # валидация таблицы
    if validationResult == True:
        return csvTable_DataFrame
    else:
        return validationResult

#Метод, который рисует график зависимости между двумя нужными столцами
#На вход принимает таблицу типа DataFrame, которую надо отрисовать
#Метод требует предварительную валидацию вводных данных, иначе кинет экспешн
def drawTableGraph(table):
    global lastSuccessfulTable

    XColumn = table[graphTitleX].values.tolist()
    YColumn = table[graphTitleY].values.tolist()

    line_chart = pygal.Line(x_title=graphTitleX, y_title=graphTitleY)
    line_chart.title = f'{graphTitleY} vs {graphTitleX}'
    line_chart.x_labels = XColumn
    line_chart.add(graphTitleY, YColumn)
    chart_url = line_chart.render_data_uri()

    lastSuccessfulTable = chart_url     # если мы дошли сюда, значит ошибк не было и можно бэкапить

    return chart_url




@app.route('/', methods=['GET', 'POST'])
def index():
    global lastSuccessfulTable  # для доступа к глобальной перемной

    # кейс 1: пользователь нажал на кнопку "добавить файл"
    if request.method == 'POST':
        # Пользователь загрузил файл
        file = request.files['file']

        if file:
            # Читаем данные файла из объекта BytesIO (чтобы не сохранять на сервере)
            # csv_data_io = BytesIO(file.read())
            file.save(uploadedFilePath)

            table = csvToDataFrame(uploadedFilePath)   # Передаем BytesIO перменную вместо пути к файлу
            if isinstance(table, pd.DataFrame):
                chart_url = drawTableGraph(table)
                return render_template('index.html', chart_url=chart_url)
            else:
                error_message = f"Ошибка валидации csv файла: {table[1]}"
                return render_template('index.html', error_message=error_message, chart_url=lastSuccessfulTable)
        error_message = "Добавленный Вами файл не распознан"
        return render_template('index.html', error_message=error_message, chart_url=lastSuccessfulTable)

    # кейс 2: # кейс 1: пользователь еще не нажимал на кнопку "добавить файл"
    else:
        table = csvToDataFrame(defaultTablePath)
        if isinstance(table, pd.DataFrame):
            chart_url = drawTableGraph(table)
            return render_template('index.html', chart_url=chart_url)
        else:
            raise Exception(f"Внимание! Стандартный scv файл для примера не прошел валидацию: {table[1]}") # table[1] - значит, что обращаемся ко второму элементу кортежа



if __name__ == '__main__':
    app.run()
