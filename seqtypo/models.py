
from datetime import date, datetime
import re
from abc import ABC, abstractmethod
import itertools
from typing import List, Optional, Literal, Dict
from pydantic import AnyUrl, Field
from pydantic.dataclasses import dataclass
from enum import Enum

# This module provides the basics models for the API. They are all dataclasses to storage the responses
#TODO: Hay que crear un sistema que permita reconocer los atributos que son URLs

NAME = 'name'
DESCRIPTION = 'description'
HREF = 'href'


class SchemeCategory(Enum):
    MLST = 'MLST'
    CGMLST = 'cgMLST'
    OTHERS = 'others'


class DatabaseCategory(Enum):
    SEQDEF = 'seqdef'
    SEQDEF_LARGE = 'sequence/profile definitions'
    ISOLATES = 'isolates'
    OTHERS = 'others'


def determine_category(description: str) -> str:
    if SchemeCategory.CGMLST.value in description:
        return SchemeCategory.CGMLST.value
    elif SchemeCategory.MLST.value in description:
        return SchemeCategory.MLST.value
    else:
        return SchemeCategory.OTHERS.value

# Tipos de clases del módulo:

# Clase Api-independientes:
#   - ModelList: Este grupo de clases está pensado para emular listas pero con métodos específicos que operen sobre los modelos
#                Las distintas subclases de ModelList otorgan funcionalidad a los elementos de la API que devuelven listas de entidades
#                Además, sirven como elementos de respuesta para las entidades de la API que necesitan devolver colecciones de elementos.

# Clase Api-Dependientes (Endpoints)
# Estas clases dependen de la configuración de la API 
#   - Entidades básicas: dataclasses que representan a las entidades básicas de cada elemento de la API
#   - FullEntities: En ocasiones, una misma entidad tiene dos representaciones en la API. Una básica, contenida en la respuesta del elemento
#       de jerarquía superior, y otro más desarrollado, al que generalmente se accede mediante un URI del anterior. Las entidades desarrolladas son las FullEntities
#   -Collections: Entidades de la API que se caracterizan por ser colecciones de una o más entidades básicas con metadata adicional. 
#       Las entidades básicas se almacenan en ModelLists mediante especializaciones de los post_init

class ModelList(ABC):

    def __init__(self, data: List):

        self.data = data
        self.model = self._get_model()

    def __post_init__(self):
        self._validate_input(self.data)
    # Hay que poner un método de búsqueda estricto

    def search(self, attr: str, pattern: Optional[str] = None, category: Optional[str] = None, 
               exact_match: bool = True, use_regex: bool = False) -> 'ModelList':
        
        filtered_data = self.data
        
        if pattern:
            if use_regex:
                regex = re.compile(pattern)
                filtered_data = [data for data in filtered_data if regex.search(getattr(data, attr))]
            else:
                if exact_match:
                    filtered_data = [data for data in filtered_data if pattern == getattr(data, attr)]
                else:
                    filtered_data = [data for data in filtered_data if pattern in getattr(data, attr)]
        
        if category:
            filtered_data = [data for data in filtered_data if data.category == category]

        return self.__class__(filtered_data)

    def _validate_input(self, input_list):

        if not isinstance(input_list, list):
            raise TypeError('Input parameter must be a list')
        if not all(isinstance(input, self.model) for input in input_list):
            raise TypeError(f'All elements in input must be a {self.model} instance')
        
    def __getitem__(self, index: int):
        
        if isinstance(index, int):
            return self.data[index]
        else:
            raise TypeError("Index must be integer")
        
    def __setitem__(self, index: int, value) -> None:
        if isinstance(index, int):
            if isinstance(value, self.model):
                self.data[index] = value
            else:
                raise TypeError(f"Value must be {self.model} instance")
        else:
            raise TypeError("Index must be integer")
            
    def __delitem__(self, index: int) -> None:
        if isinstance(index, int):
            del self.data[index]
        else:
            raise TypeError("Index must be integer")
        
    def __len__(self) -> int:
        return len(self.data)
         
    def __repr__(self) -> str:
        data_repr = ', '.join(repr(data) for data in self.data)
        return f'{self.__class__.__name__}({data_repr})'
    
    def get_content(self) -> List['ApiEndpointModel']:
        return self.data
    
    def append(self, data: 'ApiEndpointModel') -> None:
        if isinstance(data, self.model):
            self.data.append(data)
        else:
            raise ValueError(f'model data must be instnace of {self.model}')
    
    def extend(self, data: List['ApiEndpointModel']) -> None:
        self._validate_input(data)
        self.data.extend(data)

    @classmethod
    def from_list_of_model_lists(cls, data: List['ModelList']) -> 'ModelList':
        data_list = [model.data for model in data]
        flatten_list = list(itertools.chain(*data_list))
        return cls(flatten_list)

    @abstractmethod
    def _get_model(self) -> 'ApiEndpointModel':
        pass

    @abstractmethod
    def _set_url_attr(self) -> str:
        pass

    def get_urls(self):
        # Generalizar este método aprovechando pydantic.AnyURL
        url_attr = self._set_url_attr()

        if not url_attr:
            raise ValueError()
        
        return [getattr(data, url_attr) for data in self.data]
    
    @classmethod
    def from_json(cls, json: List[Dict]) -> 'ModelList':
        if isinstance(json, list):
            return cls(data=json)
        else:
            raise ValueError(f'JSON object must be list object. {type(json)} provided')

@dataclass
class ApiEndpointModel(ABC):
    # TODO: definir metodo para extraer la url raíz
    
    @classmethod
    def from_json(cls, json):
        print(cls.__name__)
        if isinstance(json, dict):
            return cls(**json)
        else:
            raise ValueError('Class must be instantiaded from valid dict objects')

@dataclass
class ApiColecctionModel(ABC):

    def _set_list_model(self, attr: List[str], api_model: 'ApiEndpointModel', list_model: ModelList):

        attr_values = getattr(self, attr)
        if not isinstance(attr_values, list):
            raise ValueError('Only can set list of list attributes')
        # Declaramos la lista de modelos:
        try:
            attr_list = [api_model(**value) for value in attr_values]
        except Exception as e:
            raise ValueError(f"Error instantiating {api_model.__name__} objects: {e}")
        
        #Instanciamos la clase lista:
        list_ins = list_model(data = attr_list)
        setattr(self, attr, list_ins)
    
            

class ResourceList(ModelList):
    def _get_model(self):
        return ApiResourceModel
    
    def _set_url_attr(self) -> str:
        return None


class DatabaseList(ModelList):

    def _get_model(self):
        return DatabaseModel
    
    def _set_url_attr(self) -> str:
        return 'href'


class SchemeList(ModelList):

    def _get_model(self):
        return SchemeModel

    def get_content(self):
        for data in self.data:
            print(f'{data.description}: {data.scheme}')

    def _set_url_attr(self) -> str:
        return 'scheme'


@dataclass
class ApiResourceModel(ApiEndpointModel, ApiColecctionModel):
    # url: root
    databases: List[Dict]
    description: str
    name: str
    long_description: Optional[str] = None

    def __post_init__(self):
        self._set_list_model('databases', DatabaseModel, DatabaseList)


@dataclass
class ApiResourceCollectionModel(ApiEndpointModel, ApiColecctionModel):
    # url: root
    resources: List[Dict] = None

    def __post_init__(self):
        self._set_list_model('resources', ApiResourceModel, ResourceList)

    def __iter__(self):
        return iter(self.resources)
    
    @classmethod
    def from_json(cls, json) -> 'ApiResourceCollectionModel':
        #TODO: Hay que cambiar toda la metodología de los from_json para evitar este problema (violación de SOLID)
        if isinstance(json, list):
            return cls(resources=json)
        else:
            raise ValueError('ApiResourceCollectionModel must be instantited from list JSON objects')


@dataclass
class FullSchemeModel:
    # url: {root}/db/{DatabaseModel.name}/schemes/{id}
    id: int
    loci: List[str] #List[Loci]
    description: str
    locus_count: int
    has_primary_key_field: bool 
    primary_key_field: AnyUrl = None
    last_updated: datetime = None
    last_added: datetime = None
    profiles_csv: str = None
    records: int = None
    profiles: str = None
    fields: List[str] = None #List Fields
    curators: Optional[List[str]] = None
    category: Optional[str] = None

    def __post_init__(self):
        self.category = determine_category(self.description)

@dataclass
class SchemeModel(ApiEndpointModel):
    # No url
    scheme: AnyUrl
    description: str
    category: Optional[SchemeCategory] = None
    query_endpoint: Optional[str] = None

    def __post_init__(self):
        self.category = determine_category(self.description)
        self.query_endpoint = f'{self.scheme}/sequence'

@dataclass
class SchemeCollectionModel(ApiEndpointModel, ApiColecctionModel):
    # url: {root}/db/{DatabaseModel.name}/schemes
    records: int
    schemes: List[Dict] # Converted in SchemeModel by post_init

    def __post_init__(self):
        self._set_list_model('schemes', SchemeModel, SchemeList)

    def __iter__(self):
        return iter(self.schemes)


@dataclass
class LocusModel:
    id: str
    data_type: str
    schemes: List[SchemeModel] # Revisar esto
    coding_sequence: bool
    alleles: str
    allele_id_format: str
    length_varies: bool
    curators: List[str]
    alleles_fasta: str
    length: int


@dataclass
class AlleleModel:
    locus: LocusModel
    curator: str
    status: str
    allele_id: int
    date_entered: date
    datestamp: date
    sender: str
    sequence: str


@dataclass
class PagingModel:
    next: str
    return_all: str
    last: str


@dataclass
class AlleleCollectionModel:
    last_updated: datetime
    alleles: List[AlleleModel]
    paging: PagingModel
    records: int


@dataclass
class LociModel:
    coding_sequence: bool
    alleles: str
    schemes: List[SchemeModel]
    allele_id_format: str
    length_varies: bool
    length: int
    curators: List[str]
    alleles_fasta: str
    id: str
    data_type: str


@dataclass
class LociCollectionModel:
    records: int
    loci: List[str]
    paging: Optional[List[PagingModel]] = None

    def __post_init__(self):

        if self.paging:
            self.paging = [PagingModel(**value) for value in self.paging]


@dataclass
class FullDatabaseModel:
    # url: {root}/db/{DatabaseModel.name}
    schemes: Optional[AnyUrl]
    loci: Optional[AnyUrl]
    submissions: Optional[AnyUrl] = None
    curators: Optional[AnyUrl] = None
    isolates: Optional[AnyUrl] = None
    sequences: Optional[AnyUrl] = None
    genomes: Optional[AnyUrl] = None
    fields: Optional[AnyUrl] = None
    projects: Optional[AnyUrl] = None


@dataclass
class DatabaseModel:
    # no url
    description: str
    href: AnyUrl
    name: str
    category: Optional[DatabaseCategory] = None
    subject: Optional[str] = None

    def __post_init__(self) -> None:
        self.category = self._determine_category()
        self.subject = self._parse_subject()

    def _determine_category(self) -> str:
        if DatabaseCategory.SEQDEF.value in self.name:
            return DatabaseCategory.SEQDEF.value
        elif DatabaseCategory.ISOLATES.value in self.name:
            return DatabaseCategory.ISOLATES.value
        else:
            return DatabaseCategory.OTHERS.value

    def _parse_subject(self) -> str:
        # Lista de patrones a eliminar
        patterns_to_remove = [
            r'REST API access to ',
            r' database',
            DatabaseCategory.ISOLATES.value,
            DatabaseCategory.SEQDEF_LARGE.value,
            DatabaseCategory.SEQDEF.value
        ]

        # Limpiar la descripción
        subject = self.description
        for pattern in patterns_to_remove:
            subject = re.sub(pattern, '', subject)

        return subject.strip()




@dataclass
class TaxonModel:
    taxon: str
    taxonomy: str
    support: int
    rank: str

    def __post_init__(self):
        self.taxonomy = self.taxonomy.split(' > ')

@dataclass
class AlleleExactResult:
    allele_id: int
    href: str = None
    allele_name: str = None
    start: int = None
    end: int = None
    orientation: str = None
    length: int = None
    contig: str = None
    linked_data: Dict = None

@dataclass
class SequenceQueryResult:
    exact_matches: Dict = None # Convertir en AlleleExactResultList para dotarle de métodos
    partial_matches: Dict = None
    fields: Dict = None

    def __post_init__(self):
        exact_matches = []
        for allele, matches in self.exact_matches.items():
            exact_matches.extend([
                AlleleExactResult(allele_name=allele, **value) for value in matches
            ])
        self.exact_matches = exact_matches

@dataclass
class rMLSTResultModel(SequenceQueryResult):
    taxon_prediction: List[Dict] = None

    def __post_init__(self):

        super().__post_init__()
        if self.taxon_prediction:
            self.taxon_prediction = [TaxonModel(**value) 
                                     for value in self.taxon_prediction]

@dataclass
class SchemeQueryResult(SequenceQueryResult):
    pass