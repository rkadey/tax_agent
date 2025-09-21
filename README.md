# Ghana Tax Calculator Agent
An intelligent agent that automates Ghanaian tax calculations and generates personalized budget PDF reports, powered by LangGraph and LangChain.

## Prerequisites

Python: 3.8+ <br>
Google Chrome

## Setup
##### 1. Clone this repository

`git clone https://github.com/your-username/ghana-tax-calculator-agent.git
cd ghana-tax-calculator-agent`

##### 2. Install dependencies
`pip install -r requirements.txt`

##### 3. Set up API key (optional, for LLM budgeting)
` OPENAI_API_KEY=your-api-key-here`

##### 4. Run the agent
`python agent.py`
<br><br>
# The Workflow

##### 1. Runs 3 predefined tax scenarios

##### 2. Scrapes net income from [Ghana’s tax calculator site](https://kessir.github.io/taxcalculatorgh/)

##### 3. Generates a tailored monthly budget

##### 4. Creates a PDF report for each case

