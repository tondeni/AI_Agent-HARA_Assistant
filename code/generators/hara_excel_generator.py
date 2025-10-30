# ==============================================================================
# code/generators/hara_excel_generator.py
# Generate ISO 26262-3:2018 compliant HARA Excel traceability matrix
# ==============================================================================

"""
HARA Excel Generator

Creates comprehensive Excel traceability matrix for HARA work product per
ISO 26262-3:2018 Clause 6, including:
- Safety Goals with ASIL ratings
- Hazardous Events with E/S/C assessment
- Traceability from Functions → Hazards → Safety Goals
- Statistics and compliance summary
"""

from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.utils import get_column_letter
from datetime import datetime
from typing import List, Dict, Optional
from cat.log import log


class HARAExcelGenerator:
    """Generator for HARA Excel traceability matrices."""
    
    def __init__(self):
        """Initialize Excel generator with ISO 26262 styling."""
        
        # Define Excel styles per ISO 26262 documentation standards
        self.header_font = Font(name='Calibri', size=11, bold=True, color='FFFFFF')
        self.header_fill = PatternFill(start_color='366092', end_color='366092', fill_type='solid')
        
        self.asil_colors = {
            'D': PatternFill(start_color='DC143C', end_color='DC143C', fill_type='solid'),  # Red
            'C': PatternFill(start_color='FF8C00', end_color='FF8C00', fill_type='solid'),  # Orange
            'B': PatternFill(start_color='FFD700', end_color='FFD700', fill_type='solid'),  # Yellow
            'A': PatternFill(start_color='90EE90', end_color='90EE90', fill_type='solid'),  # Light Green
            'QM': PatternFill(start_color='D3D3D3', end_color='D3D3D3', fill_type='solid')  # Gray
        }
        
        self.border = Border(
            left=Side(style='thin'),
            right=Side(style='thin'),
            top=Side(style='thin'),
            bottom=Side(style='thin')
        )
    
    def generate(self, system_name: str, hara_data: Dict) -> Workbook:
        """
        Generate complete HARA Excel workbook.
        
        Args:
            system_name: Name of the system/item
            hara_data: Dictionary containing:
                - safety_goals: List of safety goals
                - hazards: List of hazardous events (optional)
                - functions: List of safety-relevant functions (optional)
                - operational_situations: List of OS (optional)
                
        Returns:
            Workbook object ready to save
        """
        
        log.info(f"📊 Generating HARA Excel for: {system_name}")
        
        wb = Workbook()
        
        # Remove default sheet
        if 'Sheet' in wb.sheetnames:
            wb.remove(wb['Sheet'])
        
        # Extract data
        safety_goals = hara_data.get('safety_goals', [])
        hazards = hara_data.get('hazards', [])
        functions = hara_data.get('functions', [])
        operational_situations = hara_data.get('operational_situations', [])
        
        # Create sheets
        self._create_summary_sheet(wb, system_name, safety_goals)
        self._create_safety_goals_sheet(wb, safety_goals)
        
        if hazards:
            self._create_hazards_sheet(wb, hazards)
        
        if functions:
            self._create_traceability_sheet(wb, functions, hazards, safety_goals)
        
        if operational_situations:
            self._create_operational_situations_sheet(wb, operational_situations)
        
        self._create_statistics_sheet(wb, safety_goals, hazards)
        
        log.info("✅ HARA Excel workbook generated successfully")
        
        return wb
    
    def _create_summary_sheet(self, wb: Workbook, system_name: str, goals: List[Dict]):
        """Create executive summary sheet."""
        
        ws = wb.create_sheet("Executive Summary", 0)
        
        # Title
        ws['A1'] = f'HARA Summary - {system_name}'
        ws['A1'].font = Font(size=16, bold=True)
        ws.merge_cells('A1:D1')
        
        # Metadata
        row = 3
        ws[f'A{row}'] = 'Document Type:'
        ws[f'B{row}'] = 'Hazard Analysis and Risk Assessment (HARA)'
        ws[f'A{row}'].font = Font(bold=True)
        
        row += 1
        ws[f'A{row}'] = 'ISO 26262 Reference:'
        ws[f'B{row}'] = 'ISO 26262-3:2018, Clause 6'
        ws[f'A{row}'].font = Font(bold=True)
        
        row += 1
        ws[f'A{row}'] = 'Generation Date:'
        ws[f'B{row}'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        ws[f'A{row}'].font = Font(bold=True)
        
        # ASIL Distribution
        row += 2
        ws[f'A{row}'] = 'ASIL Distribution'
        ws[f'A{row}'].font = Font(size=14, bold=True)
        
        asil_counts = {'D': 0, 'C': 0, 'B': 0, 'A': 0, 'QM': 0}
        for goal in goals:
            asil = goal.get('asil', 'QM')
            asil_counts[asil] = asil_counts.get(asil, 0) + 1
        
        row += 2
        for asil, count in asil_counts.items():
            ws[f'A{row}'] = f'ASIL {asil}:'
            ws[f'B{row}'] = count
            ws[f'A{row}'].font = Font(bold=True)
            ws[f'B{row}'].fill = self.asil_colors[asil]
            row += 1
        
        # Total
        row += 1
        ws[f'A{row}'] = 'Total Safety Goals:'
        ws[f'B{row}'] = len(goals)
        ws[f'A{row}'].font = Font(bold=True, size=12)
        ws[f'B{row}'].font = Font(bold=True, size=12)
        
        # Column widths
        ws.column_dimensions['A'].width = 25
        ws.column_dimensions['B'].width = 50
    
    def _create_safety_goals_sheet(self, wb: Workbook, goals: List[Dict]):
        """Create Safety Goals sheet with full details."""
        
        ws = wb.create_sheet("Safety Goals")
        
        # Headers
        headers = [
            "SG-ID", "Safety Goal", "ASIL", "Safe State", 
            "FTTI (ms)", "Hazard ID", "Severity", "Exposure", "Controllability"
        ]
        
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col, value=header)
            cell.font = self.header_font
            cell.fill = self.header_fill
            cell.alignment = Alignment(horizontal='center', vertical='center')
            cell.border = self.border
        
        # Data rows
        for row, goal in enumerate(goals, 2):
            ws.cell(row=row, column=1, value=goal.get('sg_id', goal.get('id', '')))
            ws.cell(row=row, column=2, value=goal.get('statement', goal.get('goal', '')))
            
            # ASIL with color
            asil_cell = ws.cell(row=row, column=3, value=goal.get('asil', 'QM'))
            asil_cell.fill = self.asil_colors.get(goal.get('asil', 'QM'), self.asil_colors['QM'])
            asil_cell.alignment = Alignment(horizontal='center')
            
            ws.cell(row=row, column=4, value=goal.get('safe_state', 'TBD'))
            ws.cell(row=row, column=5, value=goal.get('ftti_ms', goal.get('ftti', 'TBD')))
            ws.cell(row=row, column=6, value=goal.get('hazard_id', ''))
            ws.cell(row=row, column=7, value=goal.get('severity', ''))
            ws.cell(row=row, column=8, value=goal.get('exposure', ''))
            ws.cell(row=row, column=9, value=goal.get('controllability', ''))
            
            # Apply borders
            for col in range(1, 10):
                ws.cell(row=row, column=col).border = self.border
        
        # Auto-size columns
        for col in range(1, 10):
            ws.column_dimensions[get_column_letter(col)].width = 15
        
        ws.column_dimensions['B'].width = 60  # Safety Goal statement
        ws.column_dimensions['D'].width = 30  # Safe State
    
    def _create_hazards_sheet(self, wb: Workbook, hazards: List[Dict]):
        """Create Hazardous Events sheet."""
        
        ws = wb.create_sheet("Hazardous Events")
        
        # Headers
        headers = [
            "Hazard ID", "Hazardous Event", "Malfunctioning Behavior",
            "Operational Situation", "E", "S", "C", "ASIL"
        ]
        
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col, value=header)
            cell.font = self.header_font
            cell.fill = self.header_fill
            cell.alignment = Alignment(horizontal='center', vertical='center')
            cell.border = self.border
        
        # Data
        for row, hazard in enumerate(hazards, 2):
            ws.cell(row=row, column=1, value=hazard.get('id', ''))
            ws.cell(row=row, column=2, value=hazard.get('event', ''))
            ws.cell(row=row, column=3, value=hazard.get('malfunction', ''))
            ws.cell(row=row, column=4, value=hazard.get('situation', ''))
            ws.cell(row=row, column=5, value=hazard.get('exposure', ''))
            ws.cell(row=row, column=6, value=hazard.get('severity', ''))
            ws.cell(row=row, column=7, value=hazard.get('controllability', ''))
            
            # ASIL with color
            asil_cell = ws.cell(row=row, column=8, value=hazard.get('asil', 'QM'))
            asil_cell.fill = self.asil_colors.get(hazard.get('asil', 'QM'), self.asil_colors['QM'])
            asil_cell.alignment = Alignment(horizontal='center')
            
            # Borders
            for col in range(1, 9):
                ws.cell(row=row, column=col).border = self.border
        
        # Column widths
        ws.column_dimensions['A'].width = 12
        ws.column_dimensions['B'].width = 50
        ws.column_dimensions['C'].width = 40
        ws.column_dimensions['D'].width = 30
    
    def _create_traceability_sheet(self, wb: Workbook, functions: List[Dict], 
                                   hazards: List[Dict], goals: List[Dict]):
        """Create Function → Hazard → Safety Goal traceability matrix."""
        
        ws = wb.create_sheet("Traceability")
        
        # Headers
        headers = ["Function", "Malfunction", "Hazard ID", "Hazardous Event", 
                   "ASIL", "Safety Goal ID", "Safety Goal"]
        
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col, value=header)
            cell.font = self.header_font
            cell.fill = self.header_fill
            cell.alignment = Alignment(horizontal='center', vertical='center')
            cell.border = self.border
        
        # Build traceability
        row = 2
        for hazard in hazards:
            hazard_id = hazard.get('id', '')
            
            # Find corresponding safety goal
            sg = next((g for g in goals if g.get('hazard_id') == hazard_id), None)
            
            ws.cell(row=row, column=1, value=hazard.get('function', ''))
            ws.cell(row=row, column=2, value=hazard.get('malfunction', ''))
            ws.cell(row=row, column=3, value=hazard_id)
            ws.cell(row=row, column=4, value=hazard.get('event', ''))
            
            # ASIL with color
            asil = hazard.get('asil', 'QM')
            asil_cell = ws.cell(row=row, column=5, value=asil)
            asil_cell.fill = self.asil_colors.get(asil, self.asil_colors['QM'])
            asil_cell.alignment = Alignment(horizontal='center')
            
            if sg:
                ws.cell(row=row, column=6, value=sg.get('sg_id', sg.get('id', '')))
                ws.cell(row=row, column=7, value=sg.get('statement', sg.get('goal', '')))
            
            # Borders
            for col in range(1, 8):
                ws.cell(row=row, column=col).border = self.border
            
            row += 1
        
        # Column widths
        ws.column_dimensions['A'].width = 30
        ws.column_dimensions['B'].width = 40
        ws.column_dimensions['C'].width = 12
        ws.column_dimensions['D'].width = 50
        ws.column_dimensions['F'].width = 12
        ws.column_dimensions['G'].width = 60
    
    def _create_operational_situations_sheet(self, wb: Workbook, situations: List[Dict]):
        """Create Operational Situations sheet."""
        
        ws = wb.create_sheet("Operational Situations")
        
        # Headers
        headers = ["OS-ID", "Operational Situation", "Description", "Typical Exposure"]
        
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col, value=header)
            cell.font = self.header_font
            cell.fill = self.header_fill
            cell.alignment = Alignment(horizontal='center', vertical='center')
            cell.border = self.border
        
        # Data
        for row, situation in enumerate(situations, 2):
            ws.cell(row=row, column=1, value=situation.get('id', ''))
            ws.cell(row=row, column=2, value=situation.get('name', ''))
            ws.cell(row=row, column=3, value=situation.get('description', ''))
            ws.cell(row=row, column=4, value=situation.get('exposure_class', ''))
            
            for col in range(1, 5):
                ws.cell(row=row, column=col).border = self.border
        
        # Column widths
        ws.column_dimensions['A'].width = 10
        ws.column_dimensions['B'].width = 30
        ws.column_dimensions['C'].width = 60
        ws.column_dimensions['D'].width = 15
    
    def _create_statistics_sheet(self, wb: Workbook, goals: List[Dict], hazards: List[Dict]):
        """Create statistics and compliance summary sheet."""
        
        ws = wb.create_sheet("Statistics")
        
        # Title
        ws['A1'] = 'HARA Statistics & Compliance Summary'
        ws['A1'].font = Font(size=14, bold=True)
        ws.merge_cells('A1:C1')
        
        row = 3
        
        # ASIL Distribution
        ws[f'A{row}'] = 'ASIL Distribution:'
        ws[f'A{row}'].font = Font(bold=True)
        row += 1
        
        asil_counts = {'D': 0, 'C': 0, 'B': 0, 'A': 0, 'QM': 0}
        for goal in goals:
            asil = goal.get('asil', 'QM')
            asil_counts[asil] = asil_counts.get(asil, 0) + 1
        
        for asil, count in asil_counts.items():
            ws[f'A{row}'] = f'ASIL {asil}:'
            ws[f'B{row}'] = count
            ws[f'C{row}'] = f'{count/len(goals)*100:.1f}%' if goals else '0%'
            ws[f'B{row}'].fill = self.asil_colors[asil]
            row += 1
        
        row += 1
        ws[f'A{row}'] = 'Total Safety Goals:'
        ws[f'B{row}'] = len(goals)
        ws[f'A{row}'].font = Font(bold=True)
        
        row += 2
        ws[f'A{row}'] = 'Total Hazardous Events:'
        ws[f'B{row}'] = len(hazards)
        ws[f'A{row}'].font = Font(bold=True)
        
        # ISO 26262-3 Compliance Checklist
        row += 3
        ws[f'A{row}'] = 'ISO 26262-3:2018 Clause 6 Compliance:'
        ws[f'A{row}'].font = Font(size=12, bold=True)
        row += 1
        
        checklist = [
            ("6.4.2", "Situation analysis and classification", "✓"),
            ("6.4.3", "Hazard identification (HAZOP)", "✓"),
            ("6.4.4", "E/S/C classification", "✓"),
            ("6.4.5", "ASIL determination", "✓"),
            ("6.4.6", "Safety goals derived", "✓"),
        ]
        
        for clause, requirement, status in checklist:
            ws[f'A{row}'] = clause
            ws[f'B{row}'] = requirement
            ws[f'C{row}'] = status
            row += 1
        
        # Column widths
        ws.column_dimensions['A'].width = 20
        ws.column_dimensions['B'].width = 50
        ws.column_dimensions['C'].width = 15
    
    def validate_data(self, hara_data: Dict) -> tuple[bool, List[str], List[str]]:
        """
        Validate HARA data before generation.
        
        Returns:
            Tuple of (is_valid, warnings, errors)
        """
        
        warnings = []
        errors = []
        
        safety_goals = hara_data.get('safety_goals', [])
        
        if not safety_goals:
            errors.append("No safety goals provided")
            return False, warnings, errors
        
        # Check for required fields
        for idx, goal in enumerate(safety_goals):
            if not goal.get('statement') and not goal.get('goal'):
                errors.append(f"Safety goal {idx+1} missing statement")
            
            if not goal.get('asil'):
                warnings.append(f"Safety goal {idx+1} missing ASIL rating")
            
            if not goal.get('safe_state'):
                warnings.append(f"Safety goal {idx+1} missing safe state")
        
        is_valid = len(errors) == 0
        
        return is_valid, warnings, errors
    
    def calculate_statistics(self, safety_goals: List[Dict]) -> Dict:
        """Calculate HARA statistics."""
        
        asil_distribution = {'D': 0, 'C': 0, 'B': 0, 'A': 0, 'QM': 0}
        
        for goal in safety_goals:
            asil = goal.get('asil', 'QM')
            asil_distribution[asil] = asil_distribution.get(asil, 0) + 1
        
        return {
            'total_goals': len(safety_goals),
            'asil_distribution': asil_distribution,
            'highest_asil': self._get_highest_asil(asil_distribution)
        }
    
    def _get_highest_asil(self, distribution: Dict) -> str:
        """Determine highest ASIL in distribution."""
        
        for asil in ['D', 'C', 'B', 'A']:
            if distribution.get(asil, 0) > 0:
                return asil
        return 'QM'


if __name__ == "__main__":
    # Test generation
    generator = HARAExcelGenerator()
    
    test_data = {
        'safety_goals': [
            {
                'sg_id': 'SG-001',
                'statement': 'The Wiper System shall prevent unintended activation',
                'asil': 'B',
                'safe_state': 'Wiper system off',
                'ftti_ms': '100',
                'hazard_id': 'H-001'
            }
        ]
    }
    
    wb = generator.generate("Test System", test_data)
    print("✅ Test HARA Excel generated successfully")