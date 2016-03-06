OUT_DIR = "../lophi/protobuf/"

.PHONY: all clean machines lophi_config analysis semantic_output

all: rabbitmq machines cards lophi_config analysis semantic_output

clean:
	rm -f *.pyc

rabbitmq: rabbitmq.proto
	protoc --python_out=$(OUT_DIR) rabbitmq.proto

machines: machines.proto
	protoc --python_out=$(OUT_DIR) machines.proto

cards: cards.proto
	protoc --python_out=$(OUT_DIR) cards.proto

analysis: analysis.proto
	protoc --python_out=$(OUT_DIR) analysis.proto

sensor_output: semantic_output.proto
	protoc --python_out=$(OUT_DIR) semantic_output.proto

