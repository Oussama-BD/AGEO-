"""V3 Spark job, separate HDFS and local outputs."""
from pyspark.sql import SparkSession,functions as F
s=SparkSession.builder.appName('AGEO-Corpus25-v3').getOrCreate()
x=s.read.option('multiLine','true').json('hdfs://namenode:9000/knowledge/v3/extracted/*.json')
x=x.withColumn('_docid',F.col('document.id')).dropDuplicates(['_docid']).drop('_docid')
x=x.withColumn('graph',F.struct(F.array_distinct('graph.entities').alias('entities'),F.array_distinct('graph.relations').alias('relations')))
x.write.mode('overwrite').parquet('hdfs://namenode:9000/knowledge/v3/processed-parquet')
x.write.mode('overwrite').json('file:///project/data/experiments/v3/spark')
print('V3_SPARK_DOCUMENTS',x.count())
print('V3_SPARK_RELATIONS',x.select(F.explode('graph.relations')).count())
s.stop()
