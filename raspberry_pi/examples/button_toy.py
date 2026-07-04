#!/usr/bin/env python3
"""
Example: Button-Based Toy (Toy Type D)

Hardware requirements:
- Raspberry Pi with GPIO pins
- 3-4 hardware buttons connected to GPIO
- Speaker or headphones

This toy supports:
- Hardware buttons for different actions
- Text-to-speech responses
- No microphone needed

Button mappings:
- Button 1 (GPIO 17): "Tell me a story"
- Button 2 (GPIO 27): "What's the weather?"
- Button 3 (GPIO 22): "Help me relax"
- Button 4 (GPIO 23): Exit

Usage:
    python button_toy.py
    
    Press hardware buttons to trigger actions.
"""

import logging
import sys
import time

sys.path.insert(0, "../mqtt_voice_client")

from mqtt_voice_client import VoiceClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

logger = logging.getLogger(__name__)

# Try to import GPIO library
try:
    import RPi.GPIO as GPIO
    GPIO_AVAILABLE = True
except (ImportError, RuntimeError):
    logger.warning("RPi.GPIO not available, using keyboard simulation")
    GPIO_AVAILABLE = False


def setup_gpio():
    """Setup GPIO pins for buttons."""
    if not GPIO_AVAILABLE:
        return
    
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    
    # Setup buttons with pull-up resistors
    BUTTONS = {
        17: "Tell me a story",
        27: "What's the weather?",
        22: "Help me relax",
        23: "Exit",
    }
    
    for pin in BUTTONS.keys():
        GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    
    return BUTTONS


def main():
    # Configuration
    DEVICE_ID = "rpi-button-004"
    API_URL = "https://your-backend.run.app"  # Replace with your backend URL
    LANGUAGE = "en-IN"  # Indian English
    TTS_VOICE = "indic-english-female"
    DOMAIN = "wellbeing"
    
    logger.info("Initializing Button Toy...")
    logger.info(f"Device ID: {DEVICE_ID}")
    logger.info(f"Language: {LANGUAGE}")
    logger.info(f"Domain: {DOMAIN}")
    
    # Initialize client
    client = VoiceClient(
        device_id=DEVICE_ID,
        api_url=API_URL,
        language=LANGUAGE,
        sample_rate_hz=16000,
    )
    
    # Register device
    try:
        client.register_device(
            domain=DOMAIN,
            tts_voice=TTS_VOICE,
            tts_provider="qwen",
            capabilities={
                "stt": False,  # No microphone
                "tts": True,   # Speaker
                "chat": True,  # LLM for responses
                "streaming": False,
            },
        )
        logger.info("Device registered successfully!")
    except Exception as e:
        logger.warning(f"Registration failed (may already exist): {e}")
    
    # Setup GPIO buttons
    if GPIO_AVAILABLE:
        buttons = setup_gpio()
        logger.info("GPIO buttons configured")
    else:
        buttons = {
            1: "Tell me a story",
            2: "What's the weather?",
            3: "Help me relax",
            4: "Exit",
        }
        logger.info("Using keyboard simulation (press 1-4)")
    
    session_id = f"session-{int(time.time())}"
    
    logger.info("\n" + "="*60)
    logger.info("Button Toy Ready!")
    logger.info("="*60)
    for pin, action in buttons.items():
        logger.info(f"  Button {pin}: {action}")
    logger.info("="*60 + "\n")
    
    def handle_button(text):
        """Handle button press."""
        logger.info(f"\n🔘 Button pressed: {text}")
        
        print("🔄 Processing query...")
        response = client.text_interaction(
            text=text,
            session_id=session_id,
            play_response=True,
        )
        
        if response.get("success"):
            data = response.get("data", {})
            response_text = data.get("response_text", "")
            print(f"💬 Response: {response_text}")
            print("✓ Done\n")
        else:
            error = response.get("error", "Unknown error")
            print(f"❌ Error: {error}\n")
    
    try:
        if GPIO_AVAILABLE:
            # Real GPIO mode
            last_press = {pin: 0 for pin in buttons.keys()}
            DEBOUNCE_TIME = 0.3  # 300ms debounce
            
            while True:
                for pin, action in buttons.items():
                    if GPIO.input(pin) == GPIO.LOW:  # Button pressed (active low)
                        now = time.time()
                        if now - last_press[pin] > DEBOUNCE_TIME:
                            last_press[pin] = now
                            
                            if action == "Exit":
                                logger.info("Exit button pressed")
                                return
                            
                            handle_button(action)
                
                time.sleep(0.01)  # 10ms poll rate
        else:
            # Keyboard simulation mode
            while True:
                print("\nPress button (1-4):")
                for num, action in buttons.items():
                    print(f"  {num}: {action}")
                
                key = input("> ").strip()
                
                if key == "4" or key.lower() == "exit":
                    break
                
                button_num = int(key) if key.isdigit() else None
                if button_num in buttons:
                    handle_button(buttons[button_num])
                else:
                    print("Invalid button")
    
    except KeyboardInterrupt:
        logger.info("\n\nShutting down...")
    finally:
        if GPIO_AVAILABLE:
            GPIO.cleanup()
        client.close()
        logger.info("Goodbye!")


if __name__ == "__main__":
    main()
