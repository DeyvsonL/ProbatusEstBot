import random

import sc2
from sc2 import Race, Difficulty
from sc2.constants import *
from sc2.player import Bot, Computer
from sc2.player import Human

class ProbatusEstBot(sc2.BotAI):
    def select_target(self):
        target = self.known_enemy_structures
        if target.exists:
            return target.random.position

        target = self.known_enemy_units
        if target.exists:
            return target.random.position

        if min([u.position.distance_to(self.enemy_start_locations[0]) for u in self.units]) < 5:
            return self.enemy_start_locations[0].position

        return self.state.mineral_field.random.position

    async def on_step(self, iteration):
        cc = self.units(COMMANDCENTER)
        if not cc.exists:
            target = self.known_enemy_structures.random_or(self.enemy_start_locations[0]).position
            for unit in self.workers | self.units(HELLIONTANK):
                await self.do(unit.attack(target))
            return
        else:
            cc = cc.first


        if iteration % 50 == 0 and self.units(HELLIONTANK).amount > 2:
            target = self.select_target()
            forces = self.units(HELLIONTANK)
            if (iteration//50) % 10 == 0:
                for unit in forces:
                    await self.do(unit.attack(target))
            else:
                for unit in forces.idle:
                    await self.do(unit.attack(target))

        if self.can_afford(SCV) and self.workers.amount < 25 and cc.noqueue:
            await self.do(cc.train(SCV))

        elif self.supply_left < 3:
            if self.can_afford(SUPPLYDEPOT) and self.already_pending(SUPPLYDEPOT) < 2:
                await self.build(SUPPLYDEPOT, near=cc.position.towards(self.game_info.map_center, 8))

        if self.units(SUPPLYDEPOT).exists:
            if not self.units(BARRACKS).exists:
                if self.can_afford(BARRACKS):
                    await self.build(BARRACKS, near=cc.position.towards(self.game_info.map_center, 8))

            elif self.units(BARRACKS).exists and self.units(REFINERY).amount < 2:
                if self.can_afford(REFINERY):
                    vgs = self.state.vespene_geyser.closer_than(20.0, cc)
                    for vg in vgs:
                        if self.units(REFINERY).closer_than(1.0, vg).exists:
                            break

                        worker = self.select_build_worker(vg.position)
                        if worker is None:
                            break

                        await self.do(worker.build(REFINERY, vg))
                        break

            if self.units(BARRACKS).ready.exists:
                if self.units(FACTORY).amount < 3 and not self.already_pending(HELLIONTANK):
                    if self.can_afford(FACTORY):
                        p = cc.position.towards_with_random_angle(self.game_info.map_center, 16)
                        await self.build(FACTORY, near=p)
                if self.units(FACTORY).exists:
                    if self.can_afford(ARMORY) and not self.units(ARMORY).exists:
                        p = cc.position.towards_with_random_angle(self.game_info.map_center, 16)
                        await self.build(ARMORY, near=p)
                    if self.units(ARMORY).ready.exists:
                        if self.can_afford(STARPORT) and not self.units(STARPORT).exists:
                            p = cc.position.towards_with_random_angle(self.game_info.map_center, 16)
                            await self.build(STARPORT, near=p)

        for factory in self.units(FACTORY).ready.noqueue:
            # Reactor allows us to build two at a time
            if self.units(ARMORY).exists:
                if self.can_afford(HELLIONTANK):
                    await self.do(factory.train(HELLIONTANK))

        for a in self.units(REFINERY):
            if a.assigned_harvesters < a.ideal_harvesters:
                w = self.workers.closer_than(20, a)
                if w.exists:
                    await self.do(w.random.gather(a))

        for scv in self.units(SCV).idle:
            await self.do(scv.gather(self.state.mineral_field.closest_to(cc)))

def main():
    sc2.run_game(sc2.maps.get("Sequencer LE"), [
        # Human(Race.Terran),
        Bot(Race.Terran, ProbatusEstBot()),
        Computer(Race.Zerg, Difficulty.Easy)
    ], realtime=False)

if __name__ == '__main__':
    main()