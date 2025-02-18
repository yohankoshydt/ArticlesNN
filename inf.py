import torch
from transformers import AutoModel, AutoTokenizer

# Define paths to both models
query_model_dir = "MedCPT-Query-Encoder"
article_model_dir = "MedCPT-Article-Encoder"

# Load Query Encoder
query_tokenizer = AutoTokenizer.from_pretrained(query_model_dir)
query_model = AutoModel.from_pretrained(query_model_dir)

# Load Article Encoder
article_tokenizer = AutoTokenizer.from_pretrained(article_model_dir)
article_model = AutoModel.from_pretrained(article_model_dir)

# Move models to GPU if available
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
query_model.to(device)
article_model.to(device)

print("✅ Models Loaded Successfully!")

# Function to encode a query or article
def encode_text(text, kind):
    """
    Encodes a given text into an embedding using the specified model & tokenizer.
    Interface for both article and query encodings

    Args:
        text (str): Input text to encode
        kind (str): article/query
    
    Returns:
        numpy.ndarray: Embedding vector for the input text
    """
    if kind == 'article':
        model = article_model
        tokenizer = article_tokenizer

    elif kind == 'query':
        model = query_model
        tokenizer = query_tokenizer
    else:
        raise ValueError
    
    with torch.no_grad():
        # tokenize the queries
        encoded = tokenizer(
            [text], 
            truncation=True, 
            padding=True, 
            return_tensors='pt', 
            max_length=64,
        )

        embeds = model(**encoded).last_hidden_state[:, 0, :].numpy().tolist()
        return embeds[0]

        
 
    

# # Example Query & Article
# query_text = "What are the symptoms of diabetes?"
# article_text = "Diabetes is a chronic disease that affects millions of people worldwide."

# # Encode using both models
# query_embedding = encode_text(query_text, query_model, query_tokenizer)
# article_embedding = encode_text(article_text, article_model, article_tokenizer)

if __name__ == "__main__":

    # testing
    t = encode_text(''' Aims: To investigate whether the pharmacokinetic characteristics of semaglutide were altered in people with hepatic impairment, assessed using Child-Pugh criteria, vs those with normal hepatic function.

Methods: In this multicentre, open-label, parallel-group trial (sponsor Novo Nordisk, ClinicalTrials.gov ID NCT02210871), four groups of participants with normal hepatic function (n = 19) or mild (n = 8), moderate (n = 10) or severe (n = 7) hepatic impairment received a single, subcutaneous dose of 0.5 mg semaglutide. Semaglutide plasma concentrations were assessed frequently for 35 days after dosing. The primary endpoint was area under the semaglutide plasma concentration-time curve from time zero to infinity (AUC0-∞ ). No effect of hepatic impairment was declared if the 90% confidence interval (CI) for the between-group ratio (hepatic impairment/normal function) was within the interval 0.70 to 1.43.

Results: Semaglutide exposure was similar across all groups, with AUC0-∞ treatment ratios for mild impairment/normal function of 0.95 (90% CI 0.77, 1.16), moderate impairment/normal function 1.02 (90% CI 0.93, 1.12), and severe impairment/normal function 0.97 (90% CI 0.84, 1.12). The maximum plasma semaglutide concentration (Cmax ) did not appear to be influenced by hepatic function, with mild impairment/normal function treatment ratios of 0.99 (90% CI 0.80, 1.23), moderate impairment/normal function 1.02 (90% CI 0.88, 1.18) and severe impairment/normal function 1.15 (90% CI 0.89, 1.48; sensitivity analysis excluding one extreme semaglutide concentration: 1.05 [90% CI 0.88, 1.25]). In all, 10 participants reported 12 mild or moderate non-serious adverse events. No unexpected safety or tolerability issues were observed.

Conclusions: Semaglutide exposure did not appear to be affected by hepatic impairment, suggesting that dose adjustment may not be necessary in patients with hepatic impairment. Semaglutide was well tolerated and there were no unexpected safety issues.

Keywords: GLP-1; GLP-1 analogue; liver; pharmacokinetics; type 2 diabetes.''', 'query')
    
    print(t)
