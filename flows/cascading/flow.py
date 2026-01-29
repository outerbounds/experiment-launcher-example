from random import random

from obproject import project_trigger, ProjectFlow
from metaflow import step, card

from parameters import Parameters
from animals import ANIMALS, UNKNOWN

@project_trigger(event='launch_experiment')
class CascadingParameters(ProjectFlow, Parameters):

    @card
    @step
    def start(self):
        self.out = []
        for i in range(self.count):
            item = self.animal1 if random() < self.ratio else self.animal2
            self.out.append(ANIMALS.get(item, UNKNOWN))
        print("output:")
        print(''.join(self.out))
        self.next(self.end)

    @step
    def end(self):
        pass

if __name__ == '__main__':
    CascadingParameters()
