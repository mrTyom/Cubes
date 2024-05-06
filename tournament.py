import pandas as pd

from game import Game
from player import Player
from settings import TOURS


class Tournament():
    
    def __init__(self):
        ''' Конструктор турнира '''
        
        # Турнирная таблица
        self.statistics = pd.DataFrame()
    
    
    def start(self):
        ''' Запуск турнира '''
        
        for i in range(TOURS):

            # Создаем экземпляры класса Player с передачей имени и стратегии
            playerA = Player("Жадный")
            playerB = Player("Прозорливый")
            
            # Добавляем их в массив
            playerSet = [playerA, playerB]
            
            # Создание игры
            game = Game(playerSet)

            # Запуск игры
            winner = game.start()
            
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
        print(winner_count)