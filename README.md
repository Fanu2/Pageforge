# Khatrawan Area Calculator

A PySide6 desktop application for calculating and organizing land area **Khewat-wise**, with support for parcel-level area entry, ownership shares, final owner-area calculations, project saving, and Excel export.

## Purpose

The Khatrawan Area Calculator is designed around the structure commonly used in land-revenue records.

The application organizes information at three main levels:

1. **Khewat** – the ownership account
2. **Parcel** – the individual land parcel belonging to a Khewat
3. **Owner Share** – the ownership fraction held by each owner in a Khewat

The calculator then produces a consolidated **Final Result** showing each owner's calculated area in each Khewat.

## Land-Area Conventions

The application uses the following area conversions:

- **1 Kanal = 20 Marla**
- **1 Killa = 8 Kanal = 160 Marla**
- **1 Marla = 9 Sarshai**

All calculations are internally based on **Marla**.

For example:

```text
2 Kanal 5 Marla
= (2 × 20) + 5
= 45 Marla
```

The final result can be displayed as Killa, Kanal, Marla and Sarshai.

## Parcel Identification

Each parcel can contain:

- **Murabba**
- **Square**
- **Kanal (K)**
- **Marla (M)**
- **Khasra / Kh. No.**

In the source land-record terminology, `//` is used to represent a **Murabba or Square identifier**. These identifiers are treated as parcel references, while the actual area is entered separately in Kanal and Marla.

## Main Features

### 1. Khewat Management

The **Khewats** tab provides a summary of all Khewats.

It shows:

- Khewat number
- Description
- Number of parcels
- Total Kanal
- Total Marla
- Total calculated area

Buttons include:

- `+ Khewat`
- `Delete Khewat`

### 2. Parcel Management

The **Parcels** tab records the individual parcels belonging to a Khewat.

Each parcel records:

- Khewat
- Murabba
- Square
- Kanal
- Marla
- Total Marla
- Khasra / Kh. No.

Buttons include:

- `+ Parcel`
- `Edit Parcel`
- `Delete Parcel`

The application automatically calculates the parcel's total Marla from the Kanal and Marla values.

### 3. Ownership Management

The **Owners** tab records ownership shares.

Each entry contains:

- Owner name
- Khewat
- Ownership share
- Share as a decimal
- Khewat area
- Calculated owner area

Buttons include:

- `+ Owner Share`
- `Edit Owner`
- `Delete Owner`

Fractions such as:

```text
35/297
122/297
4/99
```

are handled as ownership shares.

The calculator checks the total ownership fraction for each Khewat.

A correctly entered Khewat should have:

```text
Total ownership share = 1.00
```

### 4. Final Result

The **Final Result** tab provides the consolidated calculation.

It shows:

- Owner
- Area in each Khewat
- Total area
- Killa
- Kanal
- Marla
- Sarshai

The result is calculated from:

```text
Owner Area = Khewat Area × Ownership Share
```

This makes it possible to see both the owner's area within each Khewat and the owner's overall area.

### 5. Project Files

Projects can be saved and reopened.

Available commands:

- `New`
- `Open`
- `Save`

Project information is stored in JSON format.

This allows the working land-record calculation to be preserved and continued later.

### 6. Excel Export

The application can export the calculated project to an `.xlsx` workbook.

The workbook contains:

- `Final Result`
- `Khewat Parcels`
- `Ownership Input`
- `Khewats`

This makes the calculated information easy to inspect, print, archive, or use for further spreadsheet work.

## Sample Khewats

The application includes a sample structure based on five Khewats:

```text
100
101
102
215
216
```

Khewats **215** and **216** are included with parcel and ownership examples from the supplied sample land-record spreadsheet.

### Khewat 215

Total area:

```text
594 Marla
```

Parcel areas:

| Kila | Kanal | Marla |
|---|---:|---:|
| 3 | 8 | 0 |
| 4/1 | 4 | 4 |
| 5 | 1 | 12 |
| 1 | 7 | 18 |
| 2 | 8 | 0 |

These parcels total:

```text
594 Marla
```

Sample ownership:

| Owner | Share | Area |
|---|---:|---:|
| Ram Singh | 35/297 | 70.00 Marla |
| Baldev kaur | 122/297 | 244.00 Marla |
| Simerjit Kaur | 23/297 | 46.00 Marla |
| Ajaib Singh | 4/99 | 24.00 Marla |
| Sat sukh jass baljeet | 35/99 | 210.00 Marla |

Total ownership:

```text
1.00
```

### Khewat 216

Total area:

```text
514 Marla
```

Parcel areas:

| Kila | Kanal | Marla |
|---|---:|---:|
| 142 | 0 | 9 |
| 247 | 1 | 16 |
| 343 | 0 | 5 |
| 23 | 7 | 11 |
| 19/1 | 3 | 18 |
| 19/2 | 4 | 4 |
| 22 | 7 | 11 |

These parcels total:

```text
514 Marla
```

Sample ownership:

| Owner | Share | Area |
|---|---:|---:|
| ram Singh | 8/735 | 5.59 Marla |
| Mithu | 8/2205 | 1.86 Marla |
| Shinder Kaur | 1/6 | 85.67 Marla |
| Malkit Singh | 1/6 | 85.67 Marla |
| Jagseer singh | 32/441 | 37.30 Marla |
| jass baljeet | 1/6 | 85.67 Marla |
| sat sukh | 1469/4410 | 171.22 Marla |
| jaskaran | 32/441 | 37.30 Marla |
| Ajaib Singh | 16/2205 | 3.73 Marla |

Total ownership:

```text
1.00
```

## Requirements

The application requires:

- Python 3
- PySide6
- openpyxl

Install the dependencies with:

```bash
pip install PySide6 openpyxl
```

## Running the Application

From the directory containing the Python file:

```bash
python khatrawan_area_calculator.py
```

On Linux, if the Python command is version-specific:

```bash
python3 khatrawan_area_calculator.py
```

## Basic Workflow

A typical workflow is:

```text
Create/Open Project
        ↓
Add Khewats
        ↓
Add Parcels
        ↓
Enter Kanal + Marla
        ↓
Check Khewat Totals
        ↓
Enter Ownership Shares
        ↓
Check Ownership = 1.00
        ↓
View Final Result
        ↓
Save Project
        ↓
Export XLSX
```

## Calculation Logic

### Parcel Area

For each parcel:

```text
Total Marla = (Kanal × 20) + Marla
```

### Khewat Area

```text
Khewat Area = Sum of all parcel areas
```

### Owner Area

```text
Owner Area = Khewat Area × Ownership Share
```

### Ownership Validation

For every Khewat:

```text
Sum of ownership shares should equal 1.00
```

This provides a useful check before relying on the final result.

## Important Notes

- The application uses **Marla as its internal calculation unit**.
- Parcel identifiers such as Murabba, Square and Khasra/Kh. No. are kept separate from the numeric area.
- Ownership fractions are calculated using exact fractional arithmetic where applicable.
- The sample data for Khewats 215 and 216 is based on the supplied `Khatrawan_Area_claculator.ods`.
- The application is intended as a calculation and organization tool; source revenue records should be checked before using results for official/legal purposes.
- The current sample contains the five Khewats 100, 101, 102, 215 and 216.

## Files

The main application file is:

```text
khatrawan_area_calculator.py
```

The sample source spreadsheet used for the Khewat 215/216 data is:

```text
Khatrawan_Area_claculator.ods
```

## Technical Notes

The application is implemented in Python with a PySide6 graphical interface.

Main areas of the program include:

- Khewat data management
- Parcel data management
- Ownership-share management
- Area conversion
- Final-result calculation
- JSON project persistence
- XLSX export

The application is deliberately structured around the land-record workflow rather than treating the spreadsheet as a simple flat table.

## Status

This version contains the sample five-Khewat structure:

```text
100, 101, 102, 215, 216
```

with Khewats **215 and 216 incorporated into the calculator**, including their parcel areas and ownership-share examples.

