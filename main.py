from tournament import Tournament


# Определяем точку входа в программу
if __name__ == "__main__":

    # Создаём турнир
    tr = Tournament()
    
    # И запускаем его
    tr.start()
    
    # Вывод отчёта
    tr.report()