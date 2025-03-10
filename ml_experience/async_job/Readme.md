The sample runs asynchronous text analysis jobs in containers and can do summarization as well as sentiment analysis.

The sample embeds language models and doesn't need outbound connectivity at run time. For it to work, you need to download the following models to the right directories prior to building the image:
- `./google-t5-small` => download from [here](https://huggingface.co/google-t5/t5-small/tree/main)
- `./distilbert-base-uncased-finetuned-sst-2-english` => download from [here](https://huggingface.co/distilbert/distilbert-base-uncased-finetuned-sst-2-english/tree/main)

You also need to provide textual source data to analyze, as well as where to output the result:
- source data table is specified via `source_table` argument
- source data unique ID column via `source_id_column`
- source data column containing the text via `source_value_column`
- the job will write out the text analysis output in a table you specify via `result_table`

For testing, we used [Google Reviews & Ratings Dataset](https://app.snowflake.com/marketplace/listing/GZT1Z125KF3/dataplex-consulting-data-products-google-reviews-ratings-dataset)