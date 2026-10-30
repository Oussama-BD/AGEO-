"""Batch Spark: raw HDFS -> textes dedoublonnes; extractions -> JSON importable Neo4j."""
from pyspark.sql import SparkSession, functions as F
spark = SparkSession.builder.appName("ScientificKnowledgeGraph").getOrCreate()
raw = spark.read.json("hdfs://namenode:9000/knowledge/raw/*.json")
clean = raw.filter(F.length(F.trim("text")) > 0).withColumn("_document_id", F.col("document.id")).dropDuplicates(["_document_id"]).drop("_document_id")
clean.write.mode("overwrite").parquet("hdfs://namenode:9000/knowledge/clean")
extracted = spark.read.option("multiLine", "true").json("hdfs://namenode:9000/knowledge/extracted/*.json")
extracted = extracted.withColumn("_document_id", F.col("document.id")).dropDuplicates(["_document_id"]).drop("_document_id").withColumn("graph",
    F.struct(F.array_distinct("graph.entities").alias("entities"),
             F.array_distinct("graph.relations").alias("relations")))
extracted.write.mode("overwrite").json("hdfs://namenode:9000/knowledge/processed")
extracted.write.mode("overwrite").json("file:///project/data/processed/spark")
print("SPARK_DOCUMENTS", extracted.count())
spark.stop()
