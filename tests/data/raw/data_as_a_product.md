---
title: "Data as a Product"
source: flink-studies
ingested: 2026-06-08
tags: [data, methodology]
type: article
compiled: false
---

# Moving to a Data as a Product Architecture

???- info "Version"
    Created 01/2025
    Update 12/2025
    
This chapter provides a practical overview of current data lake and lakehouse challenges, discusses the implementation of 'data as a product' principles, and demonstrates how real-time streaming can be effectively integrated into modern data architectures.

## Context

### Operational Data and Analytical data

The classical data landscape is split between operational data, which powers real-time applications, and analytical data, which provides historical insights for decision-making and machine learning. This separation has created complex and fragile data architectures, marked by problematic ETL processes and intricate data pipelines. The challenge lies in effectively bridging these two distinct data planes to ensure seamless data flow and integration.

<figure markdown="span">
![](./diagrams/data_op_data_planes.drawio.png){ width=700 }
<figcaption>Two data planes: real-time applications, and analytical data</figcaption>
</figure>
 
The initial data platform architecture comprised a database on one side and a data warehouse on the other, with ETL jobs facilitating data movement between them. This setup can lead to bottlenecks, especially when different teams are working on various parts of an application but all relying on the same data source. It might also complicate scalability and flexibility.

To address scaling challenges and support unstructured data, the second generation of data platforms, emerging in the mid-2000s, adopted distributed object storage, leading to the development of the Data Lake.

The medallion architecture, a three-layered approach, is a common framework for organizing data lakes. This structure, as illustrated in the figure below, is driven by several key motivations:

<figure markdown="span">
![](./diagrams/medallion_arch.drawio.png){ width=700 }
<figcaption>Medallion Architecture</figcaption>
</figure>

* Leveraging cloud object storage to accommodate large volumes of both structured and unstructured data.
* Implementing data pipelines to transform data progressively, from raw landing zones to business-level aggregates.
* Facilitating data management and governance through data cataloging and distributed query tools.
* Organizing data based on its transformation stage, rather than business domains or specific use cases.

Data product and its extension with **Data Mesh** helps to restructure those two planes with a domain and use case centric approach, and not a technology stack.

### Current Challenges

In Lakehouse or data lake architecture: 

* We observe complex ETL jobs landscape, with high failure rate.
* Not all data needs the three layers architecture, but a more service contract type of data usage. Data becoming a product like a microservice.
* There is a latency issue to get the data, we talk about T + 1 to get fresh data. The + 1 can be one day or one hour, but it has latency that may not what business requirements need.
* Simple transformations need to be done with the ETL or ELT tool with the predefined staging. Not specific use-case driven implementation of the data retrieval and processing. 
* Data are **pulled** from their sources and between layers. It could be micro-batches, or long-running batches. At the bronze layer, the data are duplicated, and there is minimum of quality control done.
* In the silver layer the filtering and transformations are also generic with no specific business context.
* The gold layer includes all data of all use cases. This is where most of the work is done for data preparation and develop higher quality level. This is the layer with a lot of demands from end-user and continuous update and new aggregation developments. 
* This is the final consumer of the data lake gold layer that are pulling the data with specific Service Level Objectives. 
* Data created at the gold level, most likely needs to be reingected to the operational databases to be visible to operation applications. This introduces the concept of **reverse ETL**. 
* Each layer may have dfferent actors responsible to process the data: data platform engineer, analytic engineers and data modelers, and at the application level, the application developers.
* Storing multiple copies of data across layers inflates cloud storage expenses. Data become quickly stale and unreliable.
* Constant movement of data through layers results in unnecessary processing and query inefficiencies.
* The operational estate is also continuously growing, by adding mobile applications, serverless functions, cloud native apps, etc...

### Core Principles for Data Mesh

To address the concerns of siloed and incompatible data, while addressing scaling to constant change of data landscape, adding more data source and consumers, adding more transformations and processing resources, the data mesh is based on four core principles:

1. Domain-oriented decentralized **data ownership** and architecture. The components are the analytical data, the metadata and the computer resources to serve it. Data ownership is linked to the DDD bounded context. For a product management use case, the bounded context of a `Product`, supports operational APIs and analytical data endpoints to address *active users, feature usage, and conversion rates*, for example: 

    <figure markdown="span">
    ![Bounded context data product](./diagrams/bd_ctx_product.drawio.png){ width=500 }
    <figcaption>Data as a product  - Bounded context</figcaption>
    </figure>

    Also multiple bounded contexts could be presented via their dependencies to other domain operational and analytical data endpoints.

1. **Data as a product**, includes clear scope definition, product ownership and metrics to ensure data quality, user acceptance, lead time for data consumption. Data as a product includes documenting the users, how they access the data, and for what kind of operations. The accountability of the data quality shifts to the source of the data. It encapsulates three structural components: **1/ code** (data pipelines, schema definitions, APIs, event processing, monitoring metrics, access control), **2/ data and metadata** in a polyglot form (events, REST, tables, graphs, batch files...), **3/ infrastructure** (to run code, store data and metadata).

    <figure markdown="span">
    ![data-product-components](./diagrams/dp_components.drawio.png)
    <figcaption>Data as a product: component view</figcaption>
    </figure>

1. **Self-serve data infrastructure as a platform**, to enable domain autonomy, as microservices are defined and orchestrated. It includes callable polyglot data storage, data products schema, data pipeline declaration and orchestration, data products lineage, compute and data locality. The capabilities includes 1/ **infrastructure provisioning** via code for storage, service accounts, access policies, server provisioning for running code and jobs, 2/ **data product interface**, declarative interfaces to manage the life cycle of a data product, 3/ **supervision plane** to present the relation between data products, support discovery, build data catalog, to execute semantic query.

    <figure markdown="span">
    ![DP-infrastructure-platform](./diagrams/infrastructure_platform.drawio.png)
    <figcaption>Data as a product: infrastructure platform</figcaption>
    </figure>

1. Federated governance to address interoperability of the data products. This needs to support decentralized and domain self-sovereignty, interoperability through standardization. 


???- warning "Moving to Kafka and real-time processing is not the full story"

    Changing the batch pipeline processing technologies to real-time processing using the medallion architecture does not solve the previously mentionned problems. We still need to shift paradign and adopt a data as a product centric architecture. The following diagram illustrates the mediallon layers, done with Flink processing and Kafka topics for storage.

    <figure markdown="span">
    ![](./diagrams/hl-rt-integration.drawio.png)
    <figcaption>Real-time intgration</figcaption>
    </figure>

    Using topics as data record storage and Flink statements for transforming, filtering and enriching to the silver layer, also using kafka topics is the same ETL approach but with different technologies. 

    Another, more detailed view, using Kafka Connectors will look like in the diagram below, where the three layers are using the Kimdall practices of source processing, intermediates and sinks.

    <figure markdown="span">
    ![](./diagrams/generic_src_to_sink_flow.drawio.png)
    <figcaption>Generic source to sink pipeline</figcaption>
    </figure>

    Even if append-logs are part of the data as a product architecture, there are more to address and to organize the component development.

## A Data Product Approach

As seen previously, domains need to host and serve their domain datasets in an easily consumable way, rather than flowing the data from domains into a centrally owned data lake or platform. Dataset from one domain may be consumed by another domains in a format suitable for its own application. Consumer pulls the dataset.

<figure markdown="span">
![](./diagrams/rti_dps.drawio.png)
 <figcaption>Data product reused by other domains</figcaption>
</figure>

So developing data as a product means shifting from push and ingest of ETL and ELT processes to serving and pull model across all domains. 

### Data as a Product

Data products serve analytical data, they are self-contained, deployable, valuable and exhibit eight characteristics:

* **Discoverable**: data consumers can easily find the data product for their use case.  A common implementation is to have a registry, a data catalogue, of all available data products with their meta information. Domain data products need to register themselves to the catalog.
* **Addressable**: with a unique address accessible programmatically. This implies to define naming convention and may be SDK code.
* **Self describable**: Clear description of the purpose and usage patterns as well as the semantics and syntax. The schema definition and registry are used for that purpose. 
* **Trustworthy**: clear definition of the [Service Level Objectives](https://en.wikipedia.org/wiki/Service-level_objective) and Service Level Indicators conformance. 
* **Native access**: adapt the data access interface to the consumer: APIs, events, SQL views, reports, widgets
* **Composable**: integrate with other data products, for joining, filtering and aggregation. Nedd to define standards for field type formatting, identifying polysemes across different domains, datasets address conventions, common metadata fields, event formats such as CloudEvents. Federated identity may also being used to keep unique identifier cross domain for a business entity.
* **Valuable**: represent a cohesive concept within its domain. Sourced from unstructured, semi-structured and structured data. To maximize value within a data mesh, data products should have narrow, specific definitions, enabling reusable blueprints and efficient management.
* **Secure**: with access control rules and enforcement, and single sign on capability.

To support the implementation of those characteristics, it is relevant to name a *domain data product owner*, who is also responsible to measure data quality, the decreased lead time of data consumption, and the data user satisfaction, or net promoter score. The most important questions a product owner should be able to answer are:

1. Who are the data users?
1. How do they use the data?
1. What are the native methods that they are comfortable with to consume the data?

Data products are not data applications, data warehouses, PDF reports, dashboards, tables (without proper metadata), or kafka topics. The data products may, and should be shared using streams, to be able to replay from sources of events and scale the consumption. 

### Elements of a Data Product

The following elements are part of a data product owner to develop and manage, with application developers:

* Metadata of what the data product is, human readable, parseable for tool to build and deploy data product to orchestration layer. This includes using naming convention, and polyglot definition. 
