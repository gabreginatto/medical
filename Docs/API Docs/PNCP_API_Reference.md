# PNCP API Reference Guide - Version 1.0

Portal Nacional de Contratações Públicas (PNCP) - API Consultation Manual

## Overview

The PNCP API provides access to public contracting data in Brazil under Law 14.133/2021, including contracts, asset sales, price registration records, and contracts.

**Protocol**: REST (Representational State Transfer) / HTTP 1.1
**Data Format**: JSON (JavaScript Object Notation)

## Access Information

### Production Environment
- **Portal**: https://pncp.gov.br
- **Technical Documentation**: https://pncp.gov.br/api/consulta/swagger-ui/index.html
- **Services Base URL**: https://pncp.gov.br/api/consulta

## Available APIs

### 1. PCA Items Query APIs

#### 1.1. Query PCA Items by Year, User ID and Superior Classification
**Endpoint**: `/v1/pca/usuario`
**Method**: GET
**Purpose**: Retrieve items from Annual Contracting Plan (PCA) by year and user

**Required Parameters**:
- `anoPca` (Integer): PCA Year
- `idUsuario` (Integer): User system identification number
- `pagina` (Integer): Page number

**Optional Parameters**:
- `codigoClassificacaoSuperior` (Text): Material class or service group code
- `tamanhoPagina` (Integer): Page size (max 500, default 500)

**Example**:
```bash
curl -X 'GET' \
'https://pncp.gov.br/api/consulta/v1/pca/usuario?anoPca=2023&idUsuario=3&codigoClassificacaoSuperior=979&pagina=1' \
-H 'accept: */*'
```

#### 1.2. Query PCA Items by Year and Superior Classification
**Endpoint**: `/v1/pca/`
**Method**: GET
**Purpose**: Retrieve items from Annual Contracting Plan by year and classification

**Required Parameters**:
- `anoPca` (Integer): PCA Year
- `codigoClassificacaoSuperior` (Text): Classification code
- `pagina` (Integer): Page number

**Optional Parameters**:
- `tamanhoPagina` (Integer): Page size (max 500)

**Example**:
```bash
curl -X 'GET' \
'https://pncp.gov.br/api/consulta/v1/pca/?anoPca=2023&codigoClassificacaoSuperior=979&pagina=1' \
-H 'accept: */*'
```

### 2. Contracting Query APIs

#### 2.1. Query Contracts by Publication Date
**Endpoint**: `/v1/contratacoes/publicacao`
**Method**: GET
**Purpose**: Query contracts published on PNCP within a date range

**Required Parameters**:
- `dataInicial` (Date): Start date (YYYYMMDD format)
- `dataFinal` (Date): End date (YYYYMMDD format)
- `codigoModalidadeContratacao` (Integer): Contracting modality code
- `pagina` (Integer): Page number

**Optional Parameters**:
- `codigoModoDisputa` (Integer): Dispute mode code
- `uf` (String): State abbreviation
- `codigoMunicipioIbge` (String): IBGE municipality code
- `cnpj` (String): Organization CNPJ
- `codigoUnidadeAdministrativa` (String): Administrative unit code
- `idUsuario` (Integer): User system ID
- `tamanhoPagina` (Integer): Page size (max 500, default 50)

**Example**:
```bash
curl -X 'GET' \
'https://pncp.gov.br/api/consulta/v1/contratacoes/publicacao?dataInicial=20230801&dataFinal=20230802&codigoModalidadeContratacao=8&uf=DF&pagina=1' \
-H 'accept: */*'
```

#### 2.2. Query Contracts with Open Proposal Period
**Endpoint**: `/v1/contratacoes/proposta`
**Method**: GET
**Purpose**: Query contracts with open proposal submission period

**Required Parameters**:
- `dataFinal` (Date): End date for consultation (YYYYMMDD)
- `codigoModalidadeContratacao` (Integer): Contracting modality code
- `pagina` (Integer): Page number

**Optional Parameters**:
- `uf` (String): State abbreviation
- `codigoMunicipioIbge` (String): IBGE municipality code
- `cnpj` (String): Organization CNPJ
- `codigoUnidadeAdministrativa` (String): Administrative unit code
- `idUsuario` (Integer): User system ID
- `tamanhoPagina` (Integer): Page size (max 500)

**Example**:
```bash
curl -X 'GET' \
'https://pncp.gov.br/api/consulta/v1/contratacoes/proposta?dataFinal=20230831&codigoModalidadeContratacao=8&pagina=1' \
-H 'accept: */*'
```

### 3. Price Registration Records API

#### 3.1. Query Price Registration Records by Validity Period
**Endpoint**: `/v1/atas`
**Method**: GET
**Purpose**: Query price registration records by validity period

**Required Parameters**:
- `dataInicial` (Date): Start date (YYYYMMDD)
- `dataFinal` (Date): End date (YYYYMMDD)
- `pagina` (Integer): Page number

**Optional Parameters**:
- `idUsuario` (Integer): User system ID
- `cnpj` (String): Organization CNPJ
- `codigoUnidadeAdministrativa` (String): Administrative unit code
- `tamanhoPagina` (Integer): Page size (max 500)

**Example**:
```bash
curl -X 'GET' \
'https://pncp.gov.br/api/consulta/v1/atas?dataInicial=20230701&dataFinal=20230831&pagina=1' \
-H 'accept: */*'
```

### 4. Contracts API

#### 4.1. Query Contracts by Publication Date
**Endpoint**: `/v1/contratos`
**Method**: GET
**Purpose**: Query contracts and/or commitments with contractual force by publication date

**Required Parameters**:
- `dataInicial` (Date): Start date (YYYYMMDD)
- `dataFinal` (Date): End date (YYYYMMDD)
- `pagina` (Integer): Page number

**Optional Parameters**:
- `cnpjOrgao` (String): Organization CNPJ
- `codigoUnidadeAdministrativa` (String): Administrative unit code
- `usuarioId` (Integer): User system ID
- `tamanhoPagina` (Integer): Page size (max 500)

**Example**:
```bash
curl -X 'GET' \
'https://pncp.gov.br/api/consulta/v1/contratos?dataInicial=20230801&dataFinal=20230831&pagina=1' \
-H 'accept: */*'
```

## Domain Tables (Reference Codes)

### Convocatory Instrument
- **1**: Edital (Notice)
- **2**: Aviso de Contratação Direta (Direct Contracting Notice)
- **3**: Ato que autoriza a Contratação Direta (Direct Contracting Authorization Act)

### Contracting Modality
- **1**: Leilão - Eletrônico (Electronic Auction)
- **2**: Diálogo Competitivo (Competitive Dialogue)
- **3**: Concurso (Contest)
- **4**: Concorrência - Eletrônica (Electronic Tender)
- **5**: Concorrência - Presencial (In-person Tender)
- **6**: Pregão - Eletrônico (Electronic Reverse Auction)
- **7**: Pregão - Presencial (In-person Reverse Auction)
- **8**: Dispensa de Licitação (Exemption from Bidding)
- **9**: Inexigibilidade (Non-requirement)
- **10**: Manifestação de Interesse (Expression of Interest)
- **11**: Pré-qualificação (Pre-qualification)
- **12**: Credenciamento (Accreditation)
- **13**: Leilão - Presencial (In-person Auction)

### Dispute Mode
- **1**: Aberto (Open)
- **2**: Fechado (Closed)
- **3**: Aberto-Fechado (Open-Closed)
- **4**: Dispensa Com Disputa (Exemption with Dispute)
- **5**: Não se aplica (Not applicable)
- **6**: Fechado-Aberto (Closed-Open)

### Judgment Criteria
- **1**: Menor preço (Lowest price)
- **2**: Maior desconto (Highest discount)
- **4**: Técnica e preço (Technical and price)
- **5**: Maior lance (Highest bid)
- **6**: Maior retorno econômico (Highest economic return)
- **7**: Não se aplica (Not applicable)
- **8**: Melhor técnica (Best technique)
- **9**: Conteúdo artístico (Artistic content)

### Contract Status
- **1**: Divulgada no PNCP (Published on PNCP)
- **2**: Revogada (Revoked)
- **3**: Anulada (Annulled)
- **4**: Suspensa (Suspended)

### Company Size
- **1**: ME (Microenterprise)
- **2**: EPP (Small Business)
- **3**: Demais (Other companies)
- **4**: Não se aplica (Not applicable - individual)
- **5**: Não informado (Not informed)

### Contract Types
- **1**: Contrato (termo inicial) (Contract - initial term)
- **2**: Comodato (Commodatum)
- **3**: Arrendamento (Lease)
- **4**: Concessão (Concession)
- **5**: Termo de Adesão (Adhesion Term)
- **6**: Convênio (Agreement)
- **7**: Empenho (Commitment)
- **8**: Outros (Others)
- **9**: Termo de Execução Descentralizada (TED)
- **10**: Acordo de Cooperação Técnica (ACT)
- **11**: Termo de Compromisso (Commitment Term)
- **12**: Carta Contrato (Contract Letter)

### Process Categories
- **1**: Cessão (Assignment)
- **2**: Compras (Purchases)
- **3**: Informática (TIC) (Information Technology)
- **4**: Internacional (International)
- **5**: Locação Imóveis (Real Estate Rental)
- **6**: Mão de Obra (Labor)
- **7**: Obras (Construction)
- **8**: Serviços (Services)
- **9**: Serviços de Engenharia (Engineering Services)
- **10**: Serviços de Saúde (Health Services)
- **11**: Alienação de bens móveis/imóveis (Asset Sales)

### PCA Item Categories
- **1**: Material
- **2**: Serviço (Service)
- **3**: Obras (Construction)
- **4**: Serviços de Engenharia (Engineering Services)
- **5**: Soluções de TIC (IT Solutions)
- **6**: Locação de Imóveis (Real Estate Rental)
- **7**: Alienação/Concessão/Permissão (Sales/Concession/Permission)
- **8**: Obras e Serviços de Engenharia (Construction and Engineering Services)

## Control Numbers Structure

### PCA Control Number
Format: `99999999999999-0-999999/9999`
- CNPJ of Organization (14 digits)
- Digit "0" (PCA marker)
- Sequential number in PNCP (6 digits)
- Year (4 digits)

### Contract Control Number
Format: `99999999999999-1-999999/9999`
- CNPJ of Organization (14 digits)
- Digit "1" (contracting marker)
- Sequential number in PNCP (6 digits)
- Year (4 digits)

### Record Control Number
Format: `99999999999999-1-999999/9999-999999`
- PNCP Contract Control Number (24 digits)
- Sequential record number in PNCP (6 digits)

### Contract Control Number
Format: `99999999999999-2-999999/9999`
- CNPJ of Organization (14 digits)
- Digit "2" (contract marker)
- Sequential number in PNCP (6 digits)
- Year (4 digits)

## Standard Return Data Structure

All APIs return paginated results with the following structure:

```json
{
  "data": [], // Array with found records
  "totalRegistros": 0, // Total records found
  "totalPaginas": 0, // Total pages needed
  "numeroPagina": 0, // Current page number
  "paginasRestantes": 0, // Remaining pages
  "empty": false // Indicates if data array is empty
}
```

## HTTP Response Codes

- **200** - OK (Success)
- **204** - No Content (Success, no data)
- **400** - Bad Request (Error)
- **422** - Unprocessable Entity (Error)
- **500** - Internal Server Error (Error)

## User Identification

To find your User ID (`idUsuario`), visit: [Portals Integrated to PNCP](https://www.gov.br/compras/pt-br/acesso-a-informacao/acoes-e-programas/pncp) and click "ID Search".

## Legal Framework

Based on Law 14.133/2021 with various articles covering:
- Art. 28 (Items I-V) - Basic contracting procedures
- Art. 74 (Various subsections) - Bidding exemptions
- Art. 75 (Various subsections) - Non-requirement cases
- Art. 76 (Various subsections) - Specific procedures
- Art. 78 (Items I-III) - Additional regulations

## Support

For integration issues, contact:
- **Central de Atendimento**: https://portaldeservicos.economia.gov.br
- **Phone**: 0800 978 9001

## Additional Resources

- **Complete Integration Manual**: Available at www.gov.br (more detailed API documentation)
- **Swagger Documentation**: https://pncp.gov.br/api/consulta/swagger-ui/index.html
- **CNBS Catalog**: https://www.gov.br/compras/pt-br/sistemas/conheca-o-compras/catalogo

---

**Note**: This reference covers the consultation APIs only. For complete functionality including data insertion and updates, refer to the full Integration Manual available on the official PNCP website.