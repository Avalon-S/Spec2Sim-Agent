
import simpy
import random

class StateMachine:
    def __init__(self, env):
        self.env = env
        self.current_state = 'Idle'
        self.request_floor = 0
        self.current_floor = 0
        self.constraints = {
            'DoorOpen_duration': 5,
            'MovingUp_increment_time': 2,
            'MovingDown_decrement_time': 2,
        }
        self.no_requests_flag = True # Default to True for initial state

    def log_transition(self, from_state, to_state, condition):
        print(f"[SIM][t={self.env.now:.2f}] TRANSITION {from_state} -> {to_state} (reason={condition})")

    def log_state_entry(self, state_name):
        print(f"[SIM][t={self.env.now:.2f}] ENTER state={state_name}")

    def log_wait(self, duration, event_name):
        print(f"[SIM][t={self.env.now:.2f}] WAIT {duration:.2f}s for {event_name}")

    def idle(self):
        self.log_state_entry('Idle')
        while True:
            # Check transitions from Idle
            if self.request_floor > self.current_floor:
                self.log_transition('Idle', 'MovingUp', 'request_floor > current_floor')
                self.current_state = 'MovingUp'
                return  # Exit the current state generator
            elif self.request_floor < self.current_floor:
                self.log_transition('Idle', 'MovingDown', 'request_floor < current_floor')
                self.current_state = 'MovingDown'
                return  # Exit the current state generator
            else:
                # Stay in Idle, yield a small timeout to allow other processes to run
                yield self.env.timeout(0.001)


    def moving_up(self):
        self.log_state_entry('MovingUp')
        duration = self.constraints.get('MovingUp_increment_time', 2) # Default to 2s if not found
        self.log_wait(duration, 'moving up to next floor')
        yield self.env.timeout(duration)
        self.current_floor += 1
        # Check transitions from MovingUp
        if self.current_floor == self.request_floor:
            self.log_transition('MovingUp', 'DoorOpen', 'current_floor == request_floor')
            self.current_state = 'DoorOpen'
            return
        else:
            # Continue moving up if not at the request floor yet
            # This logic assumes continuous movement until the target floor is reached.
            # If it needs to stop at intermediate floors, the logic would be more complex.
            # For this simulation, we will loop back to simulate continued movement in the same state.
            # We don't exit and re-enter the state.
            pass # Stay in MovingUp

    def moving_down(self):
        self.log_state_entry('MovingDown')
        duration = self.constraints.get('MovingDown_decrement_time', 2) # Default to 2s if not found
        self.log_wait(duration, 'moving down to next floor')
        yield self.env.timeout(duration)
        self.current_floor -= 1
        # Check transitions from MovingDown
        if self.current_floor == self.request_floor:
            self.log_transition('MovingDown', 'DoorOpen', 'current_floor == request_floor')
            self.current_state = 'DoorOpen'
            return
        else:
            # Continue moving down if not at the request floor yet
            pass # Stay in MovingDown

    def door_open(self):
        self.log_state_entry('DoorOpen')
        duration = self.constraints.get('DoorOpen_duration', 5) # Default to 5s if not found
        self.log_wait(duration, 'door open duration')
        yield self.env.timeout(duration)
        
        # After door open duration, check for next actions
        if self.request_floor == self.current_floor: # This condition is implicitly true if we reached DoorOpen
            self.no_requests_flag = True # Assuming no new requests while door is open

        # Check transitions from DoorOpen
        if self.no_requests_flag:
            self.log_transition('DoorOpen', 'Idle', 'no requests')
            self.current_state = 'Idle'
            return
        elif self.request_floor > self.current_floor:
            self.log_transition('DoorOpen', 'MovingUp', 'request_floor > current_floor')
            self.current_state = 'MovingUp'
            return
        elif self.request_floor < self.current_floor:
            self.log_transition('DoorOpen', 'MovingDown', 'request_floor < current_floor')
            self.current_state = 'MovingDown'
            return
        else: # Default to Idle if no other condition met (e.g. stuck at a floor with no requests)
            self.log_transition('DoorOpen', 'Idle', 'default to Idle')
            self.current_state = 'Idle'
            return


    def run(self):
        while True:
            if self.current_state == 'Idle':
                yield from self.idle()
            elif self.current_state == 'MovingUp':
                yield from self.moving_up()
            elif self.current_state == 'MovingDown':
                yield from self.moving_down()
            elif self.current_state == 'DoorOpen':
                yield from self.door_open()
            else:
                # Should not happen
                yield self.env.timeout(1)

def run_simulation():
    env = simpy.Environment()
    state_machine = StateMachine(env)

    # Use a separate process to simulate external requests (Input-Driven)
    def test_scenarios(env, sm):
        yield env.timeout(1) # Initial delay

        # Scenario 1: Move up
        print("[SIM] --- SCENARIO 1: REQUEST FLOOR 5 ---")
        sm.request_floor = 5
        sm.no_requests_flag = False # Indicate there is a request
        yield env.timeout(2) # Allow state machine to process the request

        # Scenario 2: Request floor below current (after reaching target)
        yield env.timeout(10) # Wait a bit after reaching floor 5
        sm.request_floor = 2
        sm.no_requests_flag = False
        yield env.timeout(2)

        # Scenario 3: No requests, door should close and go to Idle
        yield env.timeout(10) # Wait a bit
        sm.request_floor = sm.current_floor # Set request to current floor to simulate "no requests" for next move
        sm.no_requests_flag = True
        yield env.timeout(2)

        # Scenario 4: Request floor above current from Idle
        yield env.timeout(5)
        sm.request_floor = 7
        sm.no_requests_flag = False
        yield env.timeout(2)

        # Scenario 5: Wait at door open and no new requests
        yield env.timeout(15)
        sm.no_requests_flag = True
        yield env.timeout(2)


    print("[SIM] Starting simulation")
    env.process(state_machine.run())
    env.process(test_scenarios(env, state_machine))
    env.run(until=60) # Run for a total of 60 seconds
    print(f"[SIM] END simulation at t={env.now:.2f}")

if __name__ == '__main__':
    run_simulation()
        