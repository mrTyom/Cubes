import random

from settings import CUBES, EDGES, STEPS, WIN


class Game:
    
    def __init__(self, playerSet):
        ''' Конструктор игры '''
        
        # Массив игроков
        self.playerSet = playerSet
        
        # Начальное значение максимального счёта
        self.max_score = 0
        
        # Начальный счёт партии
        self.record = 0
        
        # Начальный ход
        self.i = 0
        
    
    @staticmethod
    def cubeCount(cubeSet):
        ''' Подсчёт одинаковых кубиков '''

        cubeCount = {}
        
        for item in cubeSet:
        
            if item in cubeCount:
                cubeCount[item] += 1
        
            else:
                cubeCount[item] = 1
        
        return cubeCount
    
    
    @staticmethod
    def grade(cubeCount):
        ''' Подсчёт количества очков '''

        score = 0
        
        for key, value in cubeCount.items():

            if value == 5:
                score = 1000

            if value == 4:
                score += key*10 + 100

            if value == 3:
                if key == 1:
                    score += 100
                else:
                    score += key*10

            if value == 2:
                if key == 5:
                    score += 5*2
                if key == 1:
                    score += 10*2
                
            if value == 1:
                if key == 5:
                    score += 5
                if key == 1:
                    score += 10

        return score 
    
    
    @staticmethod
    def roll(cubes):
        ''' Бросок '''

        # Создание случайного набора кубов
        cubeSet = random.choices(range(1, EDGES + 1), k=cubes)
        
        return cubeSet
    
    
    @staticmethod
    def checkStrike(cubeCount):
        ''' Определение небитки '''

        check = False

        # Копирование сета, чтобы при удалении ключа он не мешал итерации
        keys_to_remove = cubeCount.copy()

        for key, value in cubeCount.items():
            
            if value == 5:
                del keys_to_remove[key]

            if value == 4:
                del keys_to_remove[key]

            if value == 3:
                del keys_to_remove[key]

            if value == 2:
                del keys_to_remove[key]
            
            if value == 1:
                if key == 1:
                    del keys_to_remove[key]
                if key == 5:
                    del keys_to_remove[key]

        if not keys_to_remove:
            check = True

        return check

    
    @staticmethod
    def checkFoul(score):
        ''' Определение булки '''

        if score == 0:
            return True
        else:
            return False 
        
        
    def maxScore(self):
        ''' Определение максимального счёта у игроков '''

        # Пройдемся по каждому игроку в playerSet
        for player in self.playerSet:

            # Проверим, является ли текущий счёт игрока новым максимумом
            if player.score > self.max_score:
                max_score = player.score

        self.max_score = max_score
        return max_score
    
    
    def raffle(self, cubes):
        ''' Розыгрыш '''

        # Бросок кубкиков
        cubeSet = self.roll(cubes)
        print('Расклад: ', cubeSet)

        # Подсчёт одинаковых кубиков
        cubeSetCount = self.cubeCount(cubeSet)
        print('Подсчёт: ', cubeSetCount)

        # Подсчёт суммы очков
        score = self.grade(cubeSetCount)
        print('Очки: ', score)

        return score, cubeSetCount

        
    def start(self):
        ''' Розыгрыш партии '''

        print('Новая партия')

        # Цикл до победных очков
        while self.record < WIN:

            self.i += 1

            # Цикл по очерёдности игроков
            for player in self.playerSet:
                
                step  = 0

                print(f'Ход №{self.i} игрока {player.name}')

                # Цикл по количеству бросков
                while step < STEPS:
                    
                    step += 1
                    score = 0

                    # Розыгрыш
                    score, cubeSetCount = self.raffle(CUBES)
                    print('Очки: ', score)

                    # Определение небитки
                    if self.checkStrike(cubeSetCount):
                        step = 0
                        print('Небитка')

                    # Определение булки
                    if self.checkFoul(score):
                        step = STEPS
                        print('Булка')

                    # Суммирование очков игрока
                    player.score += score
                    print('Всего: ', player.score)

            # Определение максимального счёта
            self.record = self.maxScore()
            
            