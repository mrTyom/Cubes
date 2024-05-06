import pandas as pd

from game import Game
from player import Player
from settings import TOURS


class Tournament():
    
    def __init__(self):
        ''' Конструктор турнира '''
        
        # Турнирная таблица
        self.statistics = pd.DataFrame()
            
        # Создаем массив для хранения игроков
        self.playerSet = []

        # Параметры игроков (имя, порог, стратегия)
        player_params = [
            ("Прозорливый {}".format(i), i, 'CautiousStrategy') for i in range(0, 170, 5)
        ]

        # Создаем прозорливых игроков с помощью цикла
        for name, threshold, strategy in player_params:
            player = Player(
                name=name,
                strategy=strategy,
                threshold=threshold
            )
            self.playerSet.append(player)

        # Создаем жадного игрока
        playerA = Player(
            name="Жадный",
            strategy='GreedyStrategy'
        )

        self.playerSet.append(playerA)
 
    
    def start(self):
        ''' Запуск турнира '''
        
        for i in range(TOURS):

            # Создание игры
            self.game = Game(self.playerSet)

            # Запуск игры
            winner = self.game.start()
            
            # Печать табелей
            # self.game.report()
            print(i)
            
            # Создание строки для турнирной таблицы
            new_row = pd.DataFrame({
                'Tour'      : [i]       ,
                'winner'    : [winner]  ,
            })
            
            # Добавление новой строки в турнирную таблицу
            self.statistics = pd.concat(
                [
                    self.statistics,
                    new_row
                ],
                ignore_index = True
            )


    def report(self):
        ''' Печать отчёта '''
        
        print("Процент выигранных партий каждым игроком:")
        
        # Группируем данные по игрокам и считаем количество уникальных значений в столбце "winner"
        winner_count = self.statistics.groupby('winner').size()

        # Общее количество игр
        total_games = winner_count.sum()  

        # Вычисляем процентное соотношение, округляем до десятых
        winner_percentage = (winner_count / total_games * 100).round(decimals=1)
        
        # и выводим результат
        print(winner_percentage.sort_values(ascending=False))
