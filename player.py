class Player:

    def __init__(self, name, strategy=None):
        ''' Конструктор игрока '''
        
        self.name       = name
        self.strategy   = strategy
        
        self.score      = 0