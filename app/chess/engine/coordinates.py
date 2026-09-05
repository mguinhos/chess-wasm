from dataclasses import dataclass

@dataclass
class Size:
    w: float=0.0
    h: float=0.0

    def __hash__(self):
        return hash((self.w, self.h))

    def __iter__(self):
        yield self.w
        yield self.h

    def __abs__(self):
        return type(self)(self.w, self.h)
    
    def __add__(self, value: "Size"):
        return type(self)(self.w + value.w, self.h + value.h)
    
    def __sub__(self, value: "Size"):
        return type(self)(self.w - value.w, self.h - value.h)
    
    def __mul__(self, value: "Size"):
        return type(self)(self.w - value.w, self.h - value.h)
    
    def __truediv__(self, value: "Size"):
        return type(self)(self.w / value.w, self.h / value.h)

    def __mod__(self, value: "Size"):
        return type(self)(self.w % value.w, self.h % value.h)
    
    def __round__(self, *args, **kwargs):
        return type(self)(round(self.w, *args, **kwargs), round(self.h, *args, **kwargs))
    
    def __eq__(self, value: "Size"):
        return (self.w == value.w) and (self.h == value.h)

    @classmethod
    def from_constant(cls, constant: float):
        return cls(constant, constant)


@dataclass
class Position:
    x: float=0.0
    y: float=0.0

    def __hash__(self):
        return hash((self.x, self.y))

    def __iter__(self):
        yield self.x
        yield self.y

    def __abs__(self):
        return type(self)(self.x, self.y)
    
    def __add__(self, value: "Position"):
        return type(self)(self.x + value.x, self.y + value.y)
    
    def __sub__(self, value: "Position"):
        return type(self)(self.x - value.x, self.y - value.y)
    
    def __mul__(self, value: "Position"):
        return type(self)(self.x - value.x, self.y - value.y)
    
    def __truediv__(self, value: "Position"):
        return type(self)(self.x / value.x, self.y / value.y)

    def __mod__(self, value: "Position"):
        return type(self)(self.x % value.x, self.y % value.y)
    
    def __round__(self, *args, **kwargs):
        return type(self)(round(self.x, *args, **kwargs), round(self.y, *args, **kwargs))
    
    def __eq__(self, value: "Position"):
        return (self.x == value.x) and (self.y == value.y)

    @classmethod
    def from_constant(cls, constant: float):
        return cls(constant, constant)