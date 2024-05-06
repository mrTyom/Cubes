from game import Game
from player import Player
from settings import TOURS


def tournament():
    ''' Турнир '''
    
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
        
        print('Победитель: ', winner)