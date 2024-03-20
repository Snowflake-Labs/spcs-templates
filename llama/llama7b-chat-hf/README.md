# LLAMA2 + HF on SPCS

Launch LLAMA2 + HF on SPCS in three simple steps:

1. Configure Hugging Face account and get HF token
2. Configure your Snowflake account
3. Run a simple script

**Note: You might have issues in running this tutorial due to resource capacity limitations.
Make sure that you delete your service and compute pool after you finished!!!**

### Configure Hugging Face account and get HF token

In order to use LLAMA2 and HF you need to create account and get access to the LLAMA2 model. Use the following steps to
do this:

1. Follow https://ai.meta.com/resources/models-and-libraries/llama-downloads/ to request access to LLAMA2
   **You Don't need to download anything locally**.
2. Create HF account: https://huggingface.co
3. Follow https://huggingface.co/meta-llama/Llama-2-7b-hf to access hugging face model
4. Follow: https://huggingface.co/docs/hub/security-tokens to get token.

**Note, it might take one or two days for HF to approve your request to use LLAMA2.
You would need to wait for their email before proceeding further**

### Configure Snowflake account and environment

In order to launch LLAMA2 model you need to have the following:

1. Create or retrieve your Snowflake account name, username and password
2. Make sure that the default role that your user has will have the following permissions:

* Create Compute Pool
* Create SPCS service
* Create Stage
* Create SPCS repository


3. Download this Github repository: `git clone https://github.com/Snowflake-Labs/spcs-templates.git`

4. Make sure you have `python3` installed
5. Run `pip install -r requirements.txt`
6. **Make sure you have docker installed and running**

### Run the command

```
python snow/main.py run-setup \ 
--account $YOUR_ACCOUNT \ 
--username $YOUR_USERNAME \ 
--password $YOUR_PASSWORD \ 
--db $YOUR_DATABASE \ 
--schema $YOUR_SCHEMA  \ 
--compute-pool $NAME_OF_COMPUTE_POOL \ 
--service-name $NAME_OF_SERVICE \ 
--repo-name $NAME_OF_REPO \ 
--stage-name $NAME_OF_STAGE \ 
--hf-token $YOUR_HF_TOKEN 
```

### Cleanup resources

```
python snow/main.py cleanup \ 
--account $YOUR_ACCOUNT \ 
--username $YOUR_USERNAME \ 
--password $YOUR_PASSWORD \ 
--db $YOUR_DATABASE \ 
--schema $YOUR_SCHEMA  \ 
--compute-pool $NAME_OF_COMPUTE_POOL \ 
--service-name $NAME_OF_SERVICE
```
