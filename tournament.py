import pandas as pd

from game import Game
from player import Player
from settings import TOURS


class Tournament():
    
    def __init__(self):
        ''' Конструктор турнира '''
        
        # Турнирная таблица
        self.statistics = pd.DataFrame()
    
        # Создаем игроков
        playerA = Player(
            name="Жадный",
            strategy='GreedyStrategy'
            
        )
        
        playerB = Player(
            name="Прозорливый 5",
            strategy='CautiousStrategy',
            threshold=5
        )
        
        playerC = Player(
            name="Прозорливый 10",
            strategy='CautiousStrategy',
            threshold=10
        )        
        
        playerD = Player(
            name="Прозорливый 15",
            strategy='CautiousStrategy',
            threshold=15
        )
        
        playerE = Player(
            name="Прозорливый 20",
            strategy='CautiousStrategy',
            threshold=20
        )
        
        playerF = Player(
            name="Прозорливый 30",
            strategy='CautiousStrategy',
            threshold=30
        )
        
        playerG = Player(
            name="Прозорливый 40",
            strategy='CautiousStrategy',
            threshold=40
        )
                
        playerH = Player(
            name="Прозорливый 50",
            strategy='CautiousStrategy',
            threshold=50
        )
                        
        playerJ = Player(
            name="Прозорливый 60",
            strategy='CautiousStrategy',
            threshold=60
        )
                        
        playerK = Player(
            name="Прозорливый 80",
            strategy='CautiousStrategy',
            threshold=80
        )
                        
        playerL = Player(
            name="Прозорливый 100",
            strategy='CautiousStrategy',
            threshold=100
        )
                        
        playerM = Player(
            name="Прозорливый 110",
            strategy='CautiousStrategy',
            threshold=110
        )
        
        # Добавляем их в массив
        self.playerSet = [
            playerA,
            playerB,
            playerC,
            playerD,
            playerE,
            playerF,
            playerG,
            playerH,
            playerJ,
            playerK,
            playerL,
            playerM,
        ]
        
    
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
        
        print(self.statistics)
        
        # Группируем данные по игрокам и считаем количество уникальных значений в столбце "winner"
        winner_count = self.statistics.groupby('winner').size()

        print("Количество выигранных партий каждым игроком:")
        print(winner_count.sort_values(ascending=False))