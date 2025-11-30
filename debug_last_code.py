
import simpy
import random

class StateMachine:
    def __init__(self, env):
        self.env = env
        self.current_state = 'Idle'
        self.current_floor = 0
        self.request_floor = 0
        self.no_requests = True
        self.constraints = {
            'DoorOpen_duration': 5,
            'MovingUp_increment_interval': 2,
            'MovingDown_decrement_interval': 2,
        }
        self.state_transitions = {
            'Idle': [
                {'to': 'MovingUp', 'condition': lambda: self.request_floor > self.current_floor, 'reason': 'request_floor > current_floor'},
                {'to': 'MovingDown', 'condition': lambda: self.request_floor < self.current_floor, 'reason': 'request_floor < current_floor'}
            ],
            'MovingUp': [
                {'to': 'DoorOpen', 'condition': lambda: self.current_floor == self.request_floor, 'reason': 'current_floor == request_floor'}
            ],
            'MovingDown': [
                {'to': 'DoorOpen', 'condition': lambda: self.current_floor == self.request_floor, 'reason': 'current_floor == request_floor'}
            ],
            'DoorOpen': [
                {'to': 'Idle', 'condition': lambda: self.no_requests, 'reason': 'no_requests'},
                {'to': 'MovingUp', 'condition': lambda: self.request_floor > self.current_floor, 'reason': 'request_floor > current_floor'},
                {'to': 'MovingDown', 'condition': lambda: self.request_floor < self.current_floor, 'reason': 'request_floor < current_floor'}
            ]
        }
        print("[SIM] Starting simulation")

    def _log_transition(self, from_state, to_state, reason):
        print(f"[SIM][t={self.env.now:.2f}] TRANSITION {from_state} -> {to_state} (reason={reason})")

    def _log_state_entry(self, state_name):
        print(f"[SIM][t={self.env.now:.2f}] ENTER state={state_name}")

    def _log_wait(self, duration, event_name):
        print(f"[SIM][t={self.env.now:.2f}] WAIT {duration}s for {event_name}")

    def _log_end(self, final_state):
        print(f"[SIM][t={self.env.now:.2f}] END state={final_state}")

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
                # Should not happen if all states are covered
                yield env.timeout(1) # Prevent infinite loop

    def _check_transitions(self, current_state_name):
        possible_transitions = self.state_transitions.get(current_state_name, [])
        for transition in possible_transitions:
            if transition['condition']():
                self._log_transition(self.current_state, transition['to'], transition['reason'])
                self.current_state = transition['to']
                return True
        return False

    def idle(self):
        self._log_state_entry('Idle')
        if self._check_transitions('Idle'):
            return # Transition happened immediately
        # If no transition, wait for a request.
        # In a real system, this would be an event-driven wait.
        # For simulation purposes, we'll assume an external process sets requests.
        yield self.env.timeout(0.1) # Small timeout to yield control and allow other processes to run

    def moving_up(self):
        self._log_state_entry('MovingUp')
        increment_interval = self.constraints.get('MovingUp_increment_interval', 2)
        self._log_wait(increment_interval, 'floor_reached')
        yield self.env.timeout(increment_interval)
        self.current_floor += 1
        print(f"[SIM][t={self.env.now:.2f}] Current floor: {self.current_floor}")
        if not self._check_transitions('MovingUp'):
            # If no transition occurred, stay in MovingUp and potentially continue moving if needed
            # This logic implies that MovingUp state itself might not cause a transition
            # but rather waiting for the floor condition to be met in the next iteration.
            # For this simple model, we assume a transition will eventually occur.
            # If it doesn't, the loop will just re-enter moving_up.
            # To ensure progress, we need to re-evaluate transitions.
            # A direct yield here would be a blocking call if no transition is met.
            # The current structure relies on the external process or the loop to re-evaluate.
            # If current_floor == request_floor, the next iteration will transition.
            pass

    def moving_down(self):
        self._log_state_entry('MovingDown')
        decrement_interval = self.constraints.get('MovingDown_decrement_interval', 2)
        self._log_wait(decrement_interval, 'floor_reached')
        yield self.env.timeout(decrement_interval)
        self.current_floor -= 1
        print(f"[SIM][t={self.env.now:.2f}] Current floor: {self.current_floor}")
        if not self._check_transitions('MovingDown'):
            # Similar logic as moving_up
            pass

    def door_open(self):
        self._log_state_entry('DoorOpen')
        door_duration = self.constraints.get('DoorOpen_duration', 5)
        self._log_wait(door_duration, 'door_closed')
        yield self.env.timeout(door_duration)
        # After door duration, check for new requests or stay idle if none.
        self._check_transitions('DoorOpen')


def test_scenarios(env, state_machine):
    # Scenario: Elevator starts at floor 0, receives requests, moves, opens doors, and idles.
    print("[SIM] Starting test_scenarios")

    # Initial state: Idle, floor 0
    yield env.timeout(1)

    # Request to go up to floor 3
    state_machine.request_floor = 3
    state_machine.no_requests = False
    print(f"[SIM][t={env.now:.2f}] Received request for floor {state_machine.request_floor}")
    yield env.timeout(0.5) # Allow state machine to process the request

    # Simulate moving up
    # state_machine.current_floor will increment in moving_up state
    yield env.timeout(state_machine.constraints['MovingUp_increment_interval'] * 3 + 0.1) # Wait for it to reach floor 3

    # Request to go down to floor 1
    state_machine.request_floor = 1
    print(f"[SIM][t={env.now:.2f}] Received request for floor {state_machine.request_floor}")
    yield env.timeout(0.5) # Allow state machine to process the request

    # Simulate moving down
    # state_machine.current_floor will decrement in moving_down state
    yield env.timeout(state_machine.constraints['MovingDown_decrement_interval'] * 2 + 0.1) # Wait for it to reach floor 1

    # No more requests
    state_machine.no_requests = True
    print(f"[SIM][t={env.now:.2f}] No more requests.")
    yield env.timeout(0.5)

    # Request to go up to floor 5
    state_machine.request_floor = 5
    state_machine.no_requests = False
    print(f"[SIM][t={env.now:.2f}] Received request for floor {state_machine.request_floor}")
    yield env.timeout(0.5)

    yield env.timeout(state_machine.constraints['MovingUp_increment_interval'] * 4 + 0.1)

    # End of simulation scenario
    print("[SIM] Test scenarios finished.")


def run_simulation():
    env = simpy.Environment()
    state_machine = StateMachine(env)
    env.process(state_machine.run())
    env.process(test_scenarios(env, state_machine)) # Use test_scenarios for input-driven system
    env.run(until=30) # Run simulation for a specific duration
    state_machine._log_end(state_machine.current_state)
    print("[SIM] END simulation")

if __name__ == "__main__":
    run_simulation()
        
