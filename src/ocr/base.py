from abc import ABC, abstractmethod
class OCREngine(ABC):
    @abstractmethod
    def recognize(self,image,page_number:int): raise NotImplementedError
