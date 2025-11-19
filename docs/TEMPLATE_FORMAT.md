# Prisma Template Format Specification

## Overview
Prisma templates use the `.prisma` file extension and support line-specific replacements with variable substitution.

## Syntax

### Directives
All directives start with `@` at the beginning of a line:

- `@target <path>` - Specifies the output file path
- `@line <number>` - Replace a specific line (1-indexed)
- `@lines <start>-<end>` - Replace a line range (inclusive, 1-indexed)
- `@match "<regex>"` - Replace all lines matching the regex pattern
- `@append` - Append content to the end of the file
- `@prepend` - Prepend content to the start of the file

### Variables
Same as before, all variables are case-sensitive:

- `{colorN}` - Full hex color (e.g., `{color0}` → `#a1b2c3`)
- `{colorN.r}` - Red component 0-255
- `{colorN.g}` - Green component 0-255
- `{colorN.b}` - Blue component 0-255
- `{colorN.h}` - Hue 0-360
- `{colorN.l}` - Lightness 0-100%
- `{colorN.s}` - Saturation 0-100%

Available color names: `color0`-`color15`, `background`, `foreground`, `cursor`

### Comments
Lines starting with `#` (outside of content blocks) are comments.

## Format Structure

```prisma
# Comment
@target path/to/output/file

@line 10
Single line content with {color0}

@lines 20-25
Multi-line
content here
with {color1}

@match ".*theme-color.*"
Replacement for lines matching pattern

@append
Content to add at end

@prepend
Content to add at start
```

## Example

```prisma
@target HOME\.vscode\settings.json

@match ".*workbench.colorCustomizations.*"
    "workbench.colorCustomizations": {
        "editor.background": "{background}",
        "editor.foreground": "{foreground}"
    }

@lines 50-52
    "terminal.ansiBlack": "{color0}",
    "terminal.ansiRed": "{color1}",
    "terminal.ansiGreen": "{color2}"
```

## Behavior

1. Content for a directive starts on the line after the directive
2. Content ends when another directive is encountered or EOF
3. Empty lines in content blocks are preserved
4. Variables are replaced before applying the operation
5. Line numbers are 1-indexed
6. If target file doesn't exist, it will be created
7. Regex patterns use Python's `re` module syntax
8. Multiple @match directives can be used for different patterns
9. Operations are applied in the order they appear in the template

## Use Cases

### When to use .prisma vs .txt templates:

**Use .prisma templates when:**
- Updating specific sections of existing config files
- You want to preserve file structure and only modify color values
- Working with JSON, TOML, or other structured config formats
- You need regex-based pattern matching for flexible updates

**Use .txt templates when:**
- You want complete control over the entire output file
- The file is a complete theme/style file (like CSS)
- The file format doesn't have a stable structure

## Best Practices

1. **Use @match for flexibility**: Pattern matching is more robust than line numbers
2. **Be specific with patterns**: Use enough context to avoid false matches
3. **Test your regex**: Invalid patterns will cause errors
4. **Start simple**: Begin with basic replacements, add complexity as needed
5. **Comment your templates**: Use `#` to document what each section does
