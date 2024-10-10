from spcs_utils import init_logger, load_toml_config, get_compute_pool_type, get_connection, InputRow, \
    ModelConfiguration

from classifier import run_classifier

model_config = ModelConfiguration(
    classifier_model_name='bhadresh-savani/distilbert-base-uncased-emotion',
    embedding_model_name='',
    embedding_tokenizer_name='',
)

texts = [
    'The best way is to calculate the critical values of the function and then check that the derivative is negative to the right of the largest critical value. Then, if you have access to a graphing calculator, do a quick plot to check your answer. If everything looks good, choose \nk\n{\\displaystyle k} to be greater than the largest critical value.']
rows = [InputRow(idx, texts[idx]) for idx in range(len(texts))]
outputs = run_classifier(rows, 32, model_config)

print(outputs)
