###--LINT--#############################################################################################################

format:
	black ./src/ && ruff --fix ./src/iucom/

lint:
	black --check ./src/ && ruff ./src/iucom && mypy --install-types --non-interactive ./src/iucom/

########################################################################################################################

###--DOCKER--###########################################################################################################

build:
	docker build -t smthngslv/iucom:latest -f docker/Dockerfile .

push:
	docker push smthngslv/iucom:latest

pull:
	docker pull smthngslv/iucom:latest

prune:
	docker system prune -f

########################################################################################################################
