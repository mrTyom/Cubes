from abc import ABC, abstractmethod


class Player:

    def __init__(
        self                    ,
        name                    ,   # Имя игрока
        strategy    =   None    ,   # Выбранная стратегия
        threshold   =   5       ,   # Порог активации
    ):
        ''' Конструктор игрока '''
        
        # Имя
        self.name       = name
        
        # Используемая стратегия
        if strategy == 'GreedyStrategy':
            self.strategy = GreedyStrategy() 
        
        elif strategy == 'CautiousStrategy':
            self.strategy = CautiousStrategy()
        
        elif strategy == 'HopnessStrategy':
            self.strategy = HopnessStrategy()
        
        else:
            self.strategy = GreedyStrategy()  # Иначе используем стратегию по умолчанию
    
    
class Strategy(ABC):
    ''' Интерфейс стратегии '''
    def __init__(self, threshold=5):
        super().__init__()
        self.threshold = threshold
    
    @abstractmethod
    def solutionTake(self, score):
        pass

    @abstractmethod
    def solutionHold(self, cubeCountSet):
        pass
    
    
class GreedyStrategy(Strategy):
    ''' Жадная стратегия '''
    
    def solutionTake(self, score):
        if score > 0:
            return True
        

    def solutionHold(self, cubeCountSet):
        return False


class CautiousStrategy(Strategy):
    ''' Прозорливая стратегия '''
    
    def solutionTake(self, score):
        if score > self.threshold:
            return True
        else:
            return False

    def solutionHold(self, cubeCountSet):
        return False
        
        
class HopnessStrategy(Strategy):
    ''' Надежда на небитку '''
    
    def solutionTake(self, score):
        if score > self.threshold:
            return True
        else:
            return False

    def solutionHold(self, cubeCountSet):
        if sum(cubeCountSet) > 3:
            return True
        else:
            return False