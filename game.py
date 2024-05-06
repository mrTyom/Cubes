import random
import pandas as pd


from settings import CUBES, EDGES, STEPS, WIN


class Game:
    
    def __init__(self, playerSet):
        ''' Конструктор игры '''
        
        # Массив игроков
        self.playerSet = playerSet
        
        # Табель 
        self.table = pd.DataFrame(columns=['Player', 'Score'])
        
        # Победитель
        self.winner = None
        
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

        # Сгруппировать данные по игрокам и вычислить сумму очков каждого игрока
        player_scores = self.table.groupby('Player')['Score'].sum()

        # Найти игрока с максимальной суммой очков
        self.winner = player_scores.idxmax()
        self.record = player_scores[self.winner]
    
    
    def raffle(self, cubes):
        ''' Розыгрыш '''

        # Бросок кубкиков
        cubeSet = self.roll(cubes)

        # Подсчёт одинаковых кубиков
        cubeSetCount = self.cubeCount(cubeSet)

        # Подсчёт суммы очков
        score = self.grade(cubeSetCount)

        return score, cubeSetCount

        
    def start(self):
        ''' Розыгрыш партии '''

        # Цикл до победных очков
        while self.record < WIN:

            self.i += 1

            # Цикл по очерёдности игроков
            for player in self.playerSet:
                
                step  = 0

                # Цикл по количеству бросков
                while step < STEPS:
                    
                    step += 1
                    score = 0

                    # Розыгрыш
                    score, cubeSetCount = self.raffle(CUBES)

                    # Определение небитки
                    cs = self.checkStrike(cubeSetCount)
                    if cs:
                        step = 0

                    # Определение булки
                    cf = self.checkFoul(score)
                    if cf:
                        step = STEPS

                    # Принятие решения - записать очки?
                    if player.strategy.solutionTake(score):
                        step = STEPS
                        
                    
                    # Принятие решения - отложить очки?
                    if player.strategy.solutionHold(cubeSetCount):
                        pass

                    # Создание строки для табеля
                    new_row = pd.DataFrame({
                        'Move'          : [self.i]      ,
                        'Step'          : [step]        ,
                        'Player'        : [player.name] ,
                        'cubeSetCount'  : [cubeSetCount],
                        'Score'         : [score]       ,
                        'checkStrike'   : [cs]          ,
                        'checkFoul'     : [cf]          , 
                    })
                    
                    # Добавление новой строки в табель
                    self.table = pd.concat([self.table, new_row], ignore_index=True)

            # Определение максимального счёта
            self.maxScore()
        
        return self.winner
    
    
    def report(self):
        ''' Печать отчёта '''
        
        print(self.table)