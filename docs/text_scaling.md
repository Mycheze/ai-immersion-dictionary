# Text Scaling Feature

The AI-Powered Immersion Dictionary now includes a text scaling feature that allows users to adjust the size of text throughout the application. This feature is particularly useful for users who find the default text size too small or for those who prefer larger text for better readability.

## How to Use

1. Click the "⚙️ Settings" button in the toolbar at the top of the application
2. Use the slider to adjust the text scale factor:
   - Values below 1.0 will make text smaller
   - Values above 1.0 will make text larger
   - Default value is 1.0 (100% scale)
3. Click "Save" to apply the changes

## Technical Details

- Scale factor range: 0.8 to 1.5 (80% to 150% of original size)
- The setting is saved between sessions in the user_settings.json file
- All UI elements are scaled proportionally to maintain consistent appearance

## Implementation Notes

The text scaling feature applies to all text elements in the application, including:

- Dictionary entry display
- Headword list
- Search boxes and labels
- Sentence context panel
- Menu items and buttons

Font sizes are adjusted by multiplying the base font size by the scale factor. For example:

- Base headword font size: 16pt
- With scale factor 1.2: 16 * 1.2 = 19pt

The scale factor is a persistent setting that will be remembered between application launches.