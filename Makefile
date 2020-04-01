##############################################
# Globals
APP_PATH := .
APP_NAME := aws-resource-tagger
APP_VERSION := $(shell cat $(APP_PATH)/VERSION)
APP_ARGS :=

VENV := ./venv
VENV_DEV := ./venv_dev
JQ ?= $(shell which jq)
AWS ?= $(shell which aws)

# Function options
FN_ROLE := lambda-aws-resource-tagger
FN_NAME := aws-resource-tagger
FN_DESC := "Lambda Function to tag AWS Resources"
FN_REGION := us-east-1
FN_HANDLER := main.handler
FN_RUNTIME := python3.7
FN_TIMEOUT := 30
FN_MEM := 128
FN_ENV_VARS := {TAG_FILTER_KEYS=chaordic:role}
FN_CUSTOM_ARGS ?= 
FN_TAGS ?= "{\"Name\":\"aws-resource-tags\""

FN_SCHEDULE_MIN ?= 30


FN_ZIP_FILE := aws-resource-tagger.zip
FN_PKG_FILE := "$(PWD)/dist/$(FN_ZIP_FILE)"

##############################################
# DEV
dependences:
	@test -d $(VENV_DEV) || virtualenv -p $(shell which python3) $(VENV_DEV)
	$(VENV_DEV)/bin/pip install -r requirements.txt
	@test -d $(VENV) || virtualenv -p $(shell which python3) $(VENV)
	$(VENV)/bin/pip install -r requirements.txt

##############################################
# App buil && pack

run:
	$(VENV)/bin/python main.py


clean:
	rm *.pyc |true
	rm -rf src_lambda/ |true


.PHONY : pack
pack:
	( \
		rm -rf $(FN_PKG_FILE); \
		zip -g $(FN_ZIP_FILE) main.py aws.py; \
	)

##############################################
# Setup

define get_iam_role_arn
	$(shell $(AWS) iam list-roles | $(JQ) -c '.Roles[] | select( .RoleName | contains("$(FN_ROLE)"))' |$(JQ) .Arn |tr -d '"')
endef

define get_scheduler_rule_arn
	$(shell $(AWS) events list-rules | $(JQ) -c '.Rules[] | select( .Name | contains("$(FN_NAME)"))' |$(JQ) .Arn |tr -d '"')
endef

define get_function_arn
	$(shell $(AWS) lambda list-functions  | $(JQ) -c '.Functions[] | select( .FunctionName | contains("$(FN_NAME)"))' |$(JQ) .FunctionArn |tr -d '"')
endef


.PHONY : echo-iam-role-arn
echo-iam-role-arn:
	@echo $(call get_role_arn)


.PHONY : echo-caller-rule
echo-caller-rule:
	@echo $(call get_scheduler_rule_arn)


.PHONY : echo-function-arn
echo-function-arn:
	@echo $(call get_function_arn)


.PHONY : update-iam-role
update-iam-role:
	$(AWS) iam attach-role-policy \
		--role-name $(FN_ROLE) \
		--policy-arn "arn:aws:iam::aws:policy/AmazonEC2ReadOnlyAccess"
	$(AWS) iam attach-role-policy \
		--role-name $(FN_ROLE) \
		--policy-arn "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
	$(AWS) iam put-role-policy \
		--role-name $(FN_ROLE) \
		--policy-name "config-ro" \
		--policy-document fileb://files/policy-config.json
	$(AWS) iam put-role-policy \
		--role-name $(FN_ROLE) \
		--policy-name "cloudwatch-put-metrics" \
		--policy-document fileb://files/policy-cw.json
	$(AWS) iam put-role-policy \
		--role-name $(FN_ROLE) \
		--policy-name "ec2-create-tags" \
		--policy-document fileb://files/policy-ec2-tags.json


.PHONY : create-iam-role
create-iam-role:
	aws iam create-role \
		--role-name $(FN_ROLE) \
		--description "Execution role for Function $(FN_NAME)" \
		--assume-role-policy-document fileb://./files/assume-role-document.json
	$(MAKE) update-iam-role


.PHONY : setup-iam-role
setup-iam-role: create-iam-role update-iam-role


.PHONY : create-function
create-function:
	test -n "$(FN_ROLE)" # Empty FN_ROLE variable
	$(AWS) lambda create-function \
	--function-name $(FN_NAME) \
	--description $(FN_DESC) \
	--region $(FN_REGION) \
	--zip-file fileb://$(FN_ZIP_FILE) \
	--role $(call get_iam_role_arn) \
	--handler $(FN_HANDLER) \
	--runtime $(FN_RUNTIME) \
	--timeout $(FN_TIMEOUT) \
	--memory-size $(FN_MEM) \
	--environment "$(FN_ENV_VARS)" \
	--tags '$(FN_TAGS)' $(FN_CUSTOM_ARGS)


.PHONY: create-scheduled-rule
create-scheduled-rule:
	aws events put-rule \
		--name "$(FN_NAME)-caller-rule" \
		--schedule-expression 'rate($(FN_SCHEDULE_MIN) minutes)'


.PHONY: create-function-scheduler
create-function-scheduler:
	aws lambda add-permission \
		--function-name $(FN_NAME) \
		--statement-id $(FN_NAME)-scheduler-event \
		--action 'lambda:InvokeFunction' \
		--principal events.amazonaws.com \
		--source-arn $(call get_scheduler_rule_arn)


.PHONY: create-scheduler-target
create-scheduler-target:
	aws events put-targets \
		--rule "$(FN_NAME)-caller-rule" \
		--targets "Id"="1","Arn"="$(call get_function_arn)"


##############################################
# Deploy && Update

.PHONY : deploy-function
deploy-function: pack
	$(AWS) lambda update-function-code \
		--function-name $(FN_NAME) \
		--zip-file fileb://$(FN_ZIP_FILE) \
		--region $(FN_REGION)


.PHONY: deploy
deploy: pack deploy-function
