# Advanced LED Patterns for Storyteller Box

## Overview
This document describes the advanced LED patterns implemented for the Storyteller Box to provide richer visual feedback to users. These patterns help communicate system states, user interaction results, and important alerts.

Since the Storyteller Box has only a single LED for visual feedback, we've implemented sophisticated patterns that can convey different meanings through timing, brightness variations, and sequence patterns. This maximizes the communicative potential of the single LED.

## Pattern Types

### Basic Patterns
- **solid**: Static LED on/off 
  - Meaning: System is in normal operation mode and playing audio
  - Usage: During active playback of stories
  - Code: `led_manager.set_pattern('solid', state=True)`

- **off**: LED turned off completely
  - Meaning: Component is inactive or powered down
  - Usage: When a feature is disabled or system is shutting down
  - Code: `led_manager.set_pattern('off')`

- **blink**: Regular on/off blinking at configurable speed and duty cycle
  - Meaning: Alert or notification requiring attention
  - Usage: Simple alerts, notifications, and user feedback
  - Parameters: `period` (cycle time), `duty` (percentage of time on), `count` (number of blinks)
  - Code: `led_manager.set_pattern('blink', period=0.5, duty=0.5, count=3)`

- **breathing**: Smooth sinusoidal brightness oscillation
  - Meaning: System is in standby/idle and ready for interaction
  - Usage: Default idle state, indicating system is operational and waiting
  - Parameters: `period` (time for one full breath cycle)
  - Code: `led_manager.set_pattern('breathing', period=2.5)`

### Intermediate Patterns
- **pulse**: Quick rise to full brightness followed by gradual fade
  - Meaning: Momentary notification or acknowledgment of an event
  - Usage: Card taps, button presses, operation completion
  - Code: `led_manager.set_pattern('pulse')`

- **heartbeat**: Double pulse mimicking a heartbeat rhythm
  - Meaning: System is actively processing or "thinking"
  - Usage: During background operations or when loading content
  - Code: `led_manager.set_pattern('heartbeat')`

- **fadeout**: Gradual transition from bright to off
  - Meaning: Activity is ending or transitioning to idle
  - Usage: When stories end, during shutdown, or for soft transitions
  - Parameters: `duration` (fade time), `initial` (starting brightness)
  - Code: `led_manager.set_pattern('fadeout', duration=2.0, initial=100)`

- **progress**: Visual indicator that maintains brightness proportional to completion
  - Meaning: Operation is in progress with known completion percentage
  - Usage: Loading operations, long processes with progress tracking
  - Parameters: `percent` (completion percentage)
  - Code: `led_manager.set_pattern('progress', percent=75)`

### Advanced Patterns
- **morse**: Custom morse code pattern that can encode simple messages
  - Meaning: Encoded information or specific status code
  - Usage: Debugging, advanced status reporting, error codes
  - Parameters: `message` (text to encode in morse), `dot_duration` (timing)
  - Code: `led_manager.set_pattern('morse', message="SOS")`

- **sos**: International distress signal pattern (... --- ...)
  - Meaning: Critical system error or emergency condition
  - Usage: Critical battery, system failures, unrecoverable errors
  - Code: `led_manager.set_sos(count=2, next_pattern='breathing')`

- **rainbow**: Smooth transition through brightness levels simulating color change
  - Meaning: System is in a special state or performing complex operations
  - Usage: Loading states, background processing, transitions
  - Parameters: `speed` (animation speed), `start_hue` (initial position)
  - Code: `led_manager.set_pattern('rainbow', speed=1.0)`

- **colorshift**: Distinct transitions between specific brightness levels
  - Meaning: System is cycling through different modes or states
  - Usage: Indicating multiple options, mode changes, or state transitions
  - Parameters: `levels` (list of brightness values), `duration` (time per level)
  - Code: `led_manager.set_pattern('colorshift', levels=[20, 50, 80, 100], duration=0.3)`

- **countdown**: Visual timer with decreasing brightness
  - Meaning: Timed operation in progress with known duration
  - Usage: Shutdown sequences, timed operations, delays
  - Parameters: `duration` (total countdown time), `initial_brightness` (starting level)
  - Code: `led_manager.set_pattern('countdown', duration=5.0, initial_brightness=100)`

- **attention**: Rapid pulse sequence designed to be highly noticeable
  - Meaning: Important alert requiring immediate user attention
  - Usage: Critical notifications, errors requiring user intervention
  - Parameters: `sequence` (custom timing sequence), `count` (repeat count)
  - Code: `led_manager.set_attention_pattern(count=1)`

- **success**: Three ascending pulses with increasing brightness and duration
  - Meaning: Operation completed successfully
  - Usage: After successful card reads, operations, or user actions
  - Code: `led_manager.set_success_pattern(next_pattern='solid')`

- **error**: Three descending pulses with decreasing brightness
  - Meaning: Operation failed or error occurred
  - Usage: Failed card reads, invalid operations, recoverable errors
  - Parameters: `count` (number of error sequences to show)
  - Code: `led_manager.set_error_pattern(count=2)`

## Pattern Usage in System Context

### System State Indicators
- **Boot Sequence**: Triple pulse followed by breathing
  - Meaning: System is starting up and initializing
  - Implemented as: `led_manager.set_boot_sequence()`
  - Description: Three distinct blinks followed by a smooth transition to breathing pattern
  - When: Displayed during system startup

- **Shutdown**: Countdown with decreasing brightness
  - Meaning: System is shutting down, do not disconnect power
  - Implemented as: `led_manager.set_shutdown_sequence()`
  - Description: Slow fade out over 3 seconds
  - When: Triggered by long-press of button or critical battery level

- **Idle/Ready**: Breathing pattern
  - Meaning: System is operational and waiting for card or button input
  - Implemented as: `led_manager.set_pattern('breathing', period=2.5)`
  - Description: Smooth sinusoidal breathing pattern
  - When: Default state when no story is playing and system is ready

- **Active/Playing**: Solid on
  - Meaning: System is actively playing a story
  - Implemented as: `led_manager.set_pattern('solid', state=True)`
  - Description: LED stays on at constant brightness
  - When: During story playback

- **Paused**: Breathing pattern (same as idle but context makes meaning clear)
  - Meaning: Story playback is paused
  - Implemented as: `led_manager.set_pattern('breathing', period=2.5)`
  - Description: Same as idle pattern, context differentiates meaning
  - When: After tapping button during story playback

### User Interaction Feedback
- **Card Recognition (Valid)**: Colorshift followed by solid
  - Meaning: Valid card detected, story loading
  - Implemented as: `led_manager.set_card_sequence(is_valid=True)`
  - Description: Quick colorshift through brightness levels, then solid
  - When: Valid story card is placed on the reader

- **Card Recognition (Invalid)**: Error pattern
  - Meaning: Card detected but invalid or unreadable
  - Implemented as: `led_manager.set_card_sequence(is_valid=False)`
  - Description: Series of quick, bright flashes
  - When: Card is tapped but data is missing, corrupt, or invalid

- **Empty Card**: Slow blink pattern
  - Meaning: Card detected but contains no stories
  - Implemented as: `led_manager.set_pattern('colorshift', levels=[50, 0, 50, 0], duration=0.2, count=3)`
  - Description: Three slow blinks
  - When: Card is read successfully but no stories are available

- **Operation Success**: Success pattern (ascending pulses)
  - Meaning: Operation completed successfully
  - Implemented as: `led_manager.set_success_pattern()`
  - Description: Three pulses with increasing brightness and duration
  - When: After successful operations that need confirmation

- **Story Change**: Success pattern followed by solid
  - Meaning: New story selected and beginning playback
  - Implemented as: `led_manager.set_success_pattern(next_pattern='solid')`
  - Description: Success pattern transitioning to solid
  - When: Double-tap triggers new story selection

- **Loading/Processing**: Rainbow pattern
  - Meaning: System is working on a task with undefined completion time
  - Implemented as: `led_manager.set_loading_pattern()`
  - Description: Smooth oscillation through brightness levels
  - When: During background operations or loading processes

### Alerts and Notifications
- **General Error**: Error pattern (decreasing brightness pulses)
  - Meaning: An error occurred in operation
  - Implemented as: `led_manager.set_error_pattern()`
  - Description: Three pulses with decreasing brightness
  - When: Generic error conditions

- **Critical Alert**: SOS pattern
  - Meaning: System emergency requiring immediate attention
  - Implemented as: `led_manager.set_sos()`
  - Description: International SOS morse code pattern (... --- ...)
  - When: Critical system errors, potential data loss, or hardware issues

- **Attention Required**: Attention pattern (fast pulses with pauses)
  - Meaning: Important notification requiring user awareness
  - Implemented as: `led_manager.set_attention_pattern()`
  - Description: Rapid sequence of bright flashes with pauses
  - When: Important system events that user should be aware of

- **Battery Warning (Low)**: Two short pulses, repeating
  - Meaning: Battery level below 30%, charging recommended
  - Implemented as: `led_manager.set_battery_warning(level)` with level 15-30
  - Description: Two quick flashes every few seconds
  - When: Battery level falls below 30%

- **Battery Warning (Critical)**: SOS followed by shutdown sequence
  - Meaning: Battery critically low, imminent shutdown
  - Implemented as: `led_manager.set_battery_warning(level)` with level <15
  - Description: SOS pattern followed by slow fadeout
  - When: Battery level falls below 15%, preceding automatic shutdown

- **Story Finished**: Fadeout to breathing
  - Meaning: Story playback has completed
  - Implemented as: `led_manager.set_pattern('fadeout', duration=1.0, next_pattern='breathing')`
  - Description: Smooth fade from solid to breathing pattern
  - When: At the end of story playback

## Pattern Customization and Advanced Features

### Common Parameters for All Patterns
Most patterns support the following optional parameters:

- **count**: Number of iterations before transitioning to next pattern
  ```python
  # Blink 5 times then return to breathing pattern
  led_manager.set_pattern('blink', period=0.2, count=5, next_pattern='breathing')
  ```

- **next_pattern**: Pattern to transition to after completion
  ```python
  # Show success pattern then transition to solid
  led_manager.set_pattern('success', next_pattern='solid')
  ```

- **callback**: Function to call after pattern completes
  ```python
  # Execute a function after pattern finishes
  led_manager.set_pattern('blink', count=3, callback=my_function)
  ```

### Pattern-Specific Parameters

- **blink** pattern:
  - `period`: Total time for one on-off cycle (seconds)
  - `duty`: Percentage of cycle time spent in "on" state (0.0-1.0)
  
- **breathing** pattern:
  - `period`: Time for one complete breath cycle (seconds)
  
- **pulse** pattern:
  - `stages`: Number of brightness steps in the pulse
  
- **morse** pattern:
  - `message`: Text to encode in morse code
  - `dot_duration`: Duration of a single dot unit (seconds)

- **fadeout** pattern:
  - `duration`: Total time for complete fade (seconds)
  - `initial`: Starting brightness level (0-100)

- **rainbow** pattern:
  - `speed`: Animation speed multiplier
  - `start_hue`: Starting position in virtual color wheel (0-360)

- **colorshift** pattern:
  - `levels`: List of brightness values to cycle through
  - `duration`: Time spent at each brightness level (seconds)

- **countdown** pattern:
  - `duration`: Total countdown time (seconds)
  - `initial_brightness`: Starting brightness level (0-100)

- **attention**, **success**, **error** patterns:
  - `sequence`: Custom timing sequence for advanced customization

### Custom Pattern Sequences

For the most advanced customization, you can define custom sequences for patterns like `attention`, `success`, and `error`. A sequence is a list of tuples containing brightness level and duration:

```python
# Define a custom attention sequence
custom_sequence = [
    (100, 0.05),  # Full brightness for 50ms
    (0, 0.05),    # Off for 50ms
    (100, 0.1),   # Full brightness for 100ms
    (0, 0.3),     # Off for 300ms
]

# Apply the custom sequence
led_manager.set_pattern('attention', sequence=custom_sequence, count=2)
```

### Convenience Methods

The `LedPatternManager` class provides several convenience methods that wrap common pattern configurations:

- `set_boot_sequence()`: Show boot initialization pattern
- `set_card_recognized()`: Show card recognition pattern
- `set_shutdown()`: Show shutdown sequence
- `set_sos(count, next_pattern)`: Show SOS emergency pattern
- `set_success_pattern(next_pattern)`: Show success indication
- `set_error_pattern(count, next_pattern)`: Show error indication
- `set_attention_pattern(count, next_pattern)`: Show attention-grabbing pattern
- `set_loading_pattern(duration)`: Show loading/processing pattern
- `set_card_sequence(is_valid)`: Show card recognition feedback
- `set_battery_warning(level)`: Show appropriate battery warning

### Implementation Details

These patterns are implemented in the `LedPatternManager` class in `src/utils/led_utils.py`. The implementation follows these principles:

1. **Modularity**: Each pattern is self-contained and can be switched instantly
2. **Efficient updates**: All patterns run from the main loop with minimal processing
3. **Graceful transitions**: Patterns can automatically transition to other patterns
4. **State preservation**: LED hardware state is always properly maintained
5. **PWM capability**: Uses hardware PWM for smooth brightness control when available

### Integration with Hardware Abstraction Layer

The patterns work with both real hardware (Raspberry Pi) and mock implementations for development and testing. The `LedPatternManager` interfaces with the hardware abstraction layer (HAL) through a `Button` object that provides the following LED control methods:

- `set_led(state)`: Turn LED on or off
- `start_led_pwm(duty_cycle_percent, frequency)`: Start PWM at specified duty cycle
- `stop_led_pwm()`: Stop PWM and turn LED off
- `change_led_pwm_duty_cycle(duty_cycle_percent)`: Change PWM duty cycle

## Tips for Using LED Patterns Effectively

1. **Consistent conventions**: Use the same patterns for the same meanings throughout the application
2. **Pattern duration**: Keep patterns brief enough to be responsive but long enough to be noticeable
3. **Pattern contrast**: Ensure different patterns are visually distinct from each other
4. **Context awareness**: Consider what the user is currently doing when choosing patterns
5. **Responsiveness**: Always provide immediate visual feedback for user actions
6. **Pattern transitions**: Use smooth transitions between states for a polished experience
7. **Documentation**: Keep this document updated when adding new patterns
