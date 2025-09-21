import os
import time
from typing import TypedDict, List, Dict, Any
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
from langgraph.graph import StateGraph, START, END
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.schema import HumanMessage
import re
import json
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.units import inch


class AgentState(TypedDict):
    scenario_id: int
    salary: float
    allowances: float
    tax_relief: float
    net_income: Any
    budget: Dict[str, Any]
    pdf_path: str
    error: str

SCENARIOS = [
    {"id": 1, "salary": 4000, "allowances": 0, "tax_relief": 0},
    {"id": 2, "salary": 8000, "allowances": 1000, "tax_relief": 200},
    {"id": 3, "salary": 15000, "allowances": 2500, "tax_relief": 500}
]


class GhanaTaxAgent:
    def __init__(self, llm_api_key: str = None):
        """Initialize the Ghana Tax Agent with optional LLM API key"""
        self.llm_api_key = llm_api_key
        self.llm = None
        self.driver = None
        
        if llm_api_key:
            try:
                self.llm = ChatOpenAI(
                    api_key=llm_api_key,
                    model="gpt-3.5-turbo",
                    temperature=0.7
                )
            except Exception as e:
                print(f"LLM initialization failed: {e}. Using fallback budget generation.")
        
        self.workflow = self._build_workflow()
    
    def _build_workflow(self) -> StateGraph:
        """Build the LangGraph workflow"""
        workflow = StateGraph(AgentState)
        
        # Add nodes
        workflow.add_node("scrape_tax", self.scrape_tax_calculator)
        workflow.add_node("generate_budget", self.generate_budget)
        workflow.add_node("create_pdf", self.create_pdf)
        
        # Define edges
        workflow.add_edge("scrape_tax", "generate_budget")
        workflow.add_edge("generate_budget", "create_pdf")
        workflow.add_edge("create_pdf", END)
        
        # Set entry point
        workflow.set_entry_point("scrape_tax")
        
        return workflow.compile()
    
    def _setup_driver(self):
        """Setup Selenium Chrome driver"""
        chrome_options = Options()
        #chrome_options.add_argument("--headless")  
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])
        
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        self.wait = WebDriverWait(self.driver, 10)
    
    def _close_driver(self):
        """Close the Selenium driver"""
        if self.driver:
            self.driver.quit()
            self.driver = None

    def scrape_tax_calculator(self, state: AgentState) -> AgentState:
        """Scrape the Ghana tax calculator website using Selenium"""
        try:
            if not self.driver:
                self._setup_driver()
            
            self.driver.get("https://kessir.github.io/taxcalculatorgh/")
            time.sleep(2)  
            
            print('scraping started...')
            # Gross Income 
            salary_filled = False
            salary_selectors = [
                (By.CSS_SELECTOR, 'input[placeholder*="basic" i]'),
                (By.ID, 'gross-income'),
                (By.XPATH, '//*[@id="gross-income"]'),
                (By.XPATH, '/html/body/div/div/section/div[2]/form/div[1]/div/input')
            ]
            
            for selector_type, selector_value in salary_selectors:
                try:
                    element = self.driver.find_element(selector_type, selector_value)
                    element.clear()
                    element.send_keys(str(state["salary"]))
                    salary_filled = True
                    break
                except (NoSuchElementException, TimeoutException):
                    continue
            
            if not salary_filled:
                print(f"Warning: Could not fill salary field for scenario {state['scenario_id']}")
            
            # Allowances field
            allowances_filled = False
            allowance_selectors = [
                (By.CSS_SELECTOR, 'input[placeholder*="allowance" i]'),
                (By.CSS_SELECTOR, 'input[name*="allowance" i]'),
                (By.ID, 'allowances'),
                (By.CSS_SELECTOR, 'input[type="number"]:nth-of-type(2)'),
                (By.XPATH, '//input[contains(@placeholder, "allowance")]'),
                (By.XPATH, '//label[contains(text(), "Allowance")]/following-sibling::input')
            ]
            
            for selector_type, selector_value in allowance_selectors:
                try:
                    element = self.driver.find_element(selector_type, selector_value)
                    element.clear()
                    element.send_keys(str(state["allowances"]))
                    allowances_filled = True
                    break
                except (NoSuchElementException, TimeoutException):
                    continue
            
            if not allowances_filled:
                print(f"Warning: Could not fill allowances field for scenario {state['scenario_id']}")
            
            # Tax relief
            relief_filled = False
            relief_selectors = [
                (By.CSS_SELECTOR, 'input[placeholder*="relief" i]'),
                (By.CSS_SELECTOR, 'input[name*="relief" i]'),
                (By.ID, 'relief'),
                (By.ID, 'tax-relief'),
                (By.CSS_SELECTOR, 'input[type="number"]:nth-of-type(3)'),
                (By.XPATH, '//input[contains(@placeholder, "relief")]'),
                (By.XPATH, '//label[contains(text(), "Relief")]/following-sibling::input'),
                (By.XPATH, '//label[contains(text(), "Tax Relief")]/following-sibling::input')
            ]
            
            for selector_type, selector_value in relief_selectors:
                try:
                    element = self.driver.find_element(selector_type, selector_value)
                    element.clear()
                    element.send_keys(str(state["tax_relief"]))
                    relief_filled = True
                    break
                except (NoSuchElementException, TimeoutException):
                    continue
            
            if not relief_filled:
                print(f"Warning: Could not fill tax relief field for scenario {state['scenario_id']}")
            

            try:
                body = self.driver.find_element(By.TAG_NAME, 'body')
                body.click()
            except:
                pass
            
            time.sleep(2)  
            
            # Extract net income - look for the take-home pay result
            net_income_text = None
            result_selectors = [
                (By.XPATH, '//*[contains(text(), "Take") and contains(text(), "Home")]'),
                (By.XPATH, '//*[contains(text(), "take") and contains(text(), "home")]'),
                (By.XPATH, '//*[contains(text(), "Net") and contains(text(), "Income")]'),
                (By.XPATH, '//*[contains(text(), "net") and contains(text(), "income")]'),
                (By.CLASS_NAME, 'result'),
                (By.CLASS_NAME, 'net-income'),
                (By.CLASS_NAME, 'take-home'),
                (By.ID, 'net-income'),
                (By.ID, 'take-home'),
                (By.ID, 'result'),
                (By.CSS_SELECTOR, '.result-value'),
                (By.CSS_SELECTOR, '.net-income-value'),
                (By.CSS_SELECTOR, 'div.result'),
                (By.CSS_SELECTOR, 'span.result'),
                (By.CSS_SELECTOR, 'p.result'),
                (By.XPATH, '//div[@class="result"]'),
                (By.XPATH, '//span[@class="result"]')
            ]
            
            for selector_type, selector_value in result_selectors:
                try:
                    element = self.driver.find_element(selector_type, selector_value)
                    text = element.text
                    # Extract numeric value from text
                    numbers = re.findall(r'[\d,]+\.?\d*', text.replace(',', ''))
                    if numbers:
                        # Get the last/largest number (usually the result)
                        net_income_text = max(numbers, key=lambda x: float(x.replace(',', '')))
                        break
                except (NoSuchElementException, TimeoutException):
                    continue
            
            # If still no result, try getting all text and finding patterns
            if not net_income_text:
                page_text = self.driver.find_element(By.TAG_NAME, 'body').text
                # Look for patterns like "GHS X,XXX.XX" or numbers after keywords
                patterns = [
                    r'(?:take.*?home|net.*?income)[^\d]*?([\d,]+\.?\d*)',
                    r'GHS\s*([\d,]+\.?\d*)',
                    r'₵\s*([\d,]+\.?\d*)',
                    r'Result:?\s*([\d,]+\.?\d*)'
                ]
                
                for pattern in patterns:
                    matches = re.findall(pattern, page_text, re.IGNORECASE)
                    if matches:
                        # Get the largest number found (likely the net income)
                        net_income_text = max(matches, key=lambda x: float(x.replace(',', '')))
                        break
            
            if net_income_text:
                state["net_income"] = float(net_income_text.replace(',', ''))
            else:
                # Fallback calculation if scraping fails
                print(f"Warning: Could not scrape net income for scenario {state['scenario_id']}. Using estimate.")
                state["net_income"] = self._estimate_net_income(state)
            
            print(f"Scenario {state['scenario_id']}: Net Income = GHS {state['net_income']:.2f}")
            
        except Exception as e:
            print(f"Error scraping tax calculator: {e}")
            state["net_income"] = self._estimate_net_income(state)
            state["error"] = str(e)
        
        return state
    

    def _estimate_net_income(self, state: AgentState) -> float:
        """Estimate net income with simplified Ghana tax calculation"""
        gross = state["salary"] + state["allowances"]
        
        # Simplified Ghana tax brackets (approximate)
        tax = 0
        taxable = gross - state["tax_relief"]
        
        if taxable > 0:
            # First GHS 402: 0%
            # Next GHS 108: 5%
            # Next GHS 130: 10%
            # Next GHS 3,000: 17.5%
            # Next GHS 16,472: 25%
            # Above GHS 20,112: 30%
            
            if taxable > 402:
                tax += min(taxable - 402, 108) * 0.05
            if taxable > 510:
                tax += min(taxable - 510, 130) * 0.10
            if taxable > 640:
                tax += min(taxable - 640, 3000) * 0.175
            if taxable > 3640:
                tax += min(taxable - 3640, 16472) * 0.25
            if taxable > 20112:
                tax += (taxable - 20112) * 0.30
        
        # Deduct pension (approx 5.5% employee contribution)
        pension = gross * 0.055
        
        net_income = gross - tax - pension
        return max(net_income, 0)
    
    def generate_budget(self, state: AgentState) -> AgentState:
        """Generate budget using LLM or fallback rule-based approach"""
        net_income = state["net_income"]
        
        if self.llm:
            try:
                # Use LangChain to generate budget
                prompt = ChatPromptTemplate.from_template("""
                You are a financial advisor in Ghana. Create a monthly budget for someone with a net income of GHS {net_income:.2f}.
                
                Include these categories:
                - Housing (rent/mortgage)
                - Food & Groceries
                - Transport
                - Utilities (electricity, water, internet)
                - Healthcare
                - Education/Skills Development
                - Savings/Emergency Fund
                - Discretionary (entertainment, personal)
                
                Return a JSON object with:
                {{
                    "categories": [
                        {{"name": "category_name", "amount": amount_in_ghs, "percentage": percentage_of_income}},
                        ...
                    ],
                    "notes": "Brief advice about this budget (max 2 sentences)"
                }}
                
                Ensure the total does not exceed GHS {net_income:.2f}.
                Be realistic for Ghana's cost of living.
                """)
                
                message = prompt.format(net_income=net_income)
                response = self.llm.invoke([HumanMessage(content=message)])
                
                # Parse JSON response with better error handling
                content = response.content
                
                # Try to extract JSON from the response
                json_match = re.search(r'\{[\s\S]*\}', content)
                if json_match:
                    json_str = json_match.group(0)
                    budget_data = json.loads(json_str)
                else:
                    # Try direct parsing
                    budget_data = json.loads(content)
                
                # Validate and clean the budget data
                if "categories" in budget_data and isinstance(budget_data["categories"], list):
                    # Ensure percentages are calculated correctly
                    for category in budget_data["categories"]:
                        if "amount" in category and net_income > 0:
                            category["percentage"] = round((category["amount"] / net_income) * 100, 1)
                    state["budget"] = budget_data
                else:
                    raise ValueError("Invalid budget format from LLM")
                
            except Exception as e:
                print(f"LLM generation failed: {e}. Using fallback.")
                state["budget"] = self._generate_fallback_budget(net_income)
        else:
            state["budget"] = self._generate_fallback_budget(net_income)
        
        return state
    

    def _generate_fallback_budget(self, net_income: float) -> Dict[str, Any]:
        """Generate rule-based budget for Ghana"""
        # Percentage allocations based on income level
        if net_income <= 5000:
            allocations = {
                "Housing": 0.30,
                "Food & Groceries": 0.25,
                "Transport": 0.15,
                "Utilities": 0.10,
                "Healthcare": 0.05,
                "Education/Skills": 0.05,
                "Savings/Emergency": 0.05,
                "Discretionary": 0.05
            }
            notes = "Focus on essentials with this income level. Consider additional income sources."
        elif net_income <= 10000:
            allocations = {
                "Housing": 0.28,
                "Food & Groceries": 0.20,
                "Transport": 0.15,
                "Utilities": 0.08,
                "Healthcare": 0.06,
                "Education/Skills": 0.08,
                "Savings/Emergency": 0.10,
                "Discretionary": 0.05
            }
            notes = "Good balance between needs and savings. Build your emergency fund consistently."
        else:
            allocations = {
                "Housing": 0.25,
                "Food & Groceries": 0.15,
                "Transport": 0.12,
                "Utilities": 0.07,
                "Healthcare": 0.08,
                "Education/Skills": 0.10,
                "Savings/Emergency": 0.15,
                "Discretionary": 0.08
            }
            notes = "Strong income allows for increased savings and investments. Consider long-term financial goals."
        
        categories = []
        for name, percentage in allocations.items():
            amount = net_income * percentage
            categories.append({
                "name": name,
                "amount": round(amount, 2),
                "percentage": round(percentage * 100, 1)
            })
        
        return {
            "categories": categories,
            "notes": notes
        }
    

    def create_pdf(self, state: AgentState) -> AgentState:
        """Create PDF budget report"""
        scenario_id = state["scenario_id"]
        filename = f"budget_case{scenario_id}.pdf"
        
        doc = SimpleDocTemplate(filename, pagesize=letter)
        elements = []
        styles = getSampleStyleSheet()
        
        # Title
        title = Paragraph(f"<b>Ghana Tax & Budget Report - Case {scenario_id}</b>", styles['Title'])
        elements.append(title)
        elements.append(Spacer(1, 0.3*inch))
        
        # Date
        date = Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d')}", styles['Normal'])
        elements.append(date)
        elements.append(Spacer(1, 0.3*inch))
        
        # Input Parameters
        elements.append(Paragraph("<b>Input Parameters</b>", styles['Heading2']))
        params_data = [
            ["Parameter", "Amount (GHS)"],
            ["Monthly Basic Salary", f"{state['salary']:,.2f}"],
            ["Monthly Allowances", f"{state['allowances']:,.2f}"],
            ["Tax Relief", f"{state['tax_relief']:,.2f}"],
            ["", ""],
            ["<b>Net Income (Take Home)</b>", f"<b>GHS {state['net_income']:,.2f}</b>"]
        ]
        
        params_table = Table(params_data, colWidths=[3*inch, 2*inch])
        params_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (1, 1), (1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        elements.append(params_table)
        elements.append(Spacer(1, 0.5*inch))
        
        # Monthly Budget
        elements.append(Paragraph("<b>Monthly Budget Allocation</b>", styles['Heading2']))
        
        budget_data = [["Category", "Amount (GHS)", "% of Income"]]
        total = 0
        for category in state["budget"]["categories"]:
            budget_data.append([
                category["name"],
                f"{category['amount']:,.2f}",
                f"{category['percentage']:.1f}%"
            ])
            total += category['amount']
        
        budget_data.append(["", "", ""])
        budget_data.append(["<b>Total</b>", f"<b>{total:,.2f}</b>", f"<b>{(total/state['net_income']*100):.1f}%</b>"])
        
        budget_table = Table(budget_data, colWidths=[2.5*inch, 1.5*inch, 1.5*inch])
        budget_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (1, 1), (1, -1), 'RIGHT'),
            ('ALIGN', (2, 1), (2, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('GRID', (0, 0), (-1, -3), 1, colors.black),
            ('LINEBELOW', (0, -1), (-1, -1), 2, colors.black)
        ]))
        elements.append(budget_table)
        elements.append(Spacer(1, 0.3*inch))
        
        # Notes
        elements.append(Paragraph("<b>Budget Notes</b>", styles['Heading2']))
        notes_text = state["budget"]["notes"]
        elements.append(Paragraph(notes_text, styles['Normal']))
        
        # Build PDF
        doc.build(elements)
        state["pdf_path"] = filename
        print(f"PDF created: {filename}")
        
        return state
    
    def process_scenario(self, scenario: Dict[str, Any]) -> AgentState:
        """Process a single scenario through the workflow"""
        initial_state = AgentState(
            scenario_id=scenario["id"],
            salary=scenario["salary"],
            allowances=scenario["allowances"],
            tax_relief=scenario["tax_relief"],
            net_income=0.0,
            budget={},
            pdf_path="",
            error=""
        )
        
        # Run the workflow
        result = self.workflow.invoke(initial_state)
        return result
    
    def run(self):
        """Run the agent for all scenarios"""
        print("Starting Ghana Tax Calculator Agent (Selenium)...")
        print("-" * 50)
        
        try:
            for scenario in SCENARIOS:
                print(f"\nProcessing Scenario {scenario['id']}...")
                print(f"  Salary: GHS {scenario['salary']:,}")
                print(f"  Allowances: GHS {scenario['allowances']:,}")
                print(f"  Tax Relief: GHS {scenario['tax_relief']:,}")
                
                result = self.process_scenario(scenario)
                
                if result.get("error"):
                    print(f"  ⚠ Warning: {result['error']}")
                
                print(f"  ✓ Net Income: GHS {result['net_income']:,.2f}")
                print(f"  ✓ Budget generated")
                print(f"  ✓ PDF created: {result['pdf_path']}")
            
            print("\n" + "=" * 50)
            print("All scenarios processed successfully!")
            print("PDFs generated: budget_case1.pdf, budget_case2.pdf, budget_case3.pdf")
        
        finally:
            # Always close the driver
            self._close_driver()


def main():
    """Main entry point"""
    # Try to load .env file
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass
    
    # Get API key from environment or use None for fallback
    api_key = os.getenv("OPENAI_API_KEY", None)
    
    if not api_key:
        print("Note: No OPENAI_API_KEY found. Using fallback budget generation.")
        print("To use AI-powered budget generation, set your OPENAI_API_KEY environment variable.")
        print("-" * 50)
    
    agent = GhanaTaxAgent(llm_api_key=api_key)
    agent.run()

if __name__ == "__main__":
    main()