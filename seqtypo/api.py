
import requests
from typing import List, Dict

import pandas as pd
from io import StringIO
from Bio import SeqIO
from . import models, utils

# This module provide the services to interact with the API. It relies in the API models

# API Docs: https://bigsdb.readthedocs.io/en/latest/rest.html
# API paper: https://academic.oup.com/database/article/doi/10.1093/database/bax060/4079979

#TODO: Hay que gestionar todo el tema de la paginación
#TODO: Hay que plantear un patrón de diseño. Posiblemente factory?
#TODO: Tema de la cache
#TODO: Gestionar mejor la deserialización de objetos (clase json parser)class JsonParser:

class ApiServiceError(Exception):
    def __init__(self, status_code, message):
        super().__init__(f"Error {status_code}: {message}")

class RestClient:
    # Thanks to https://www.pretzellogix.net/2021/12/08/step-3-understanding-wet-code-dry-code-and-refactoring-the-low-level-rest-adapter/
    """
    A low-level REST client to interact with APIs. It supports GET and POST HTTP methods, and allows setting custom headers.

    Attributes:
        _api_key (str): An API key for authentication (OAuth is recommended and might require adaptation).
        ver (str): API version, though currently, no API versioning is in use.
        _ssl_verify (bool): Indicates whether SSL certificate verification is enabled.
        _headers (dict): A dictionary of headers to be sent with each request.

    Methods:
        __init__(self, api_key: str = '', ver: str = '', ssl_verify: bool = True) -> None:
            Initializes the RestClient instance with optional API key, version, and SSL verification flag.
        
        set_headers(self, headers: Dict[str, str]) -> None:
            Updates the default headers with additional headers.
        
        _do_request(self, url: str, http_method: str, headers: Dict = None, **kwargs) -> requests.Response:
            Performs the actual HTTP request, handling the specified method (GET, POST, etc.) and managing errors.

        get(self, url: str, **kwargs) -> requests.Response:
            Sends a GET request to the specified URL.

        post(self, url: str, **kwargs) -> requests.Response:
            Sends a POST request to the specified URL.
    """


    def __init__(self, api_key: str = '', ver: str = '', ssl_verify: bool = True) -> None:
        self._api_key = api_key # Realmente es OAuth, habrá que adaptarlo
        self.ver = ver # Realmente ninguna funciona con versión...
        self._ssl_verify = ssl_verify
        self._headers = {}
    
    def set_headers(self, headers: Dict[str, str]) -> None:
        self._headers.update(headers)
    
    def _do_request(self, url, http_method: str, headers: Dict = None, **kwargs) -> requests.Response:

        try:
            headers = headers or {}
            headers.update(self._headers)
            response = requests.request(
                method=http_method, url=url, verify=self._ssl_verify, 
                headers=headers,
                **kwargs
                )
            response.raise_for_status()
            return response
        except requests.HTTPError as e:
            raise ApiServiceError(response.status_code, response.reason) from e

    def get(self,url, **kwargs) -> requests.Response:
        return self._do_request(url=url, http_method="GET", **kwargs)

    def post(self,url, **kwargs) -> requests.Response:
        return self._do_request(url=url, http_method="POST", **kwargs)


class ApiService:
    """
    A high-level API service class that provides an interface for interacting with APIs using the RestClient.

    Attributes:
        api_key (str): The API key used for authenticating requests.
        ssl_verify (bool): Indicates whether SSL certificate verification is enabled.
        rest_client (RestClient): An instance of RestClient for making HTTP requests.

    Methods:
        __init__(self, api_key: str = '', ssl_verify: bool = True) -> None:
            Initializes the ApiService instance with an API key and SSL verification flag, and creates a RestClient instance.
    """
    def __init__(self, api_key: str = '', ssl_verify: bool = True) -> None:
        self.api_key = api_key
        self.ssl_verify = ssl_verify
        self.rest_client = RestClient(api_key=self.api_key, ssl_verify=self.ssl_verify)

   
class BigSdbApi(ApiService): 
    """
    A specialized API service class for interacting with BigSdb API resources and databases.

    Attributes:
        hostname (str): The hostname of the BigSdb API.

    Methods:
        __init__(self, hostname: str = None, api_key: str = '', ssl_verify: bool = True) -> None:
            Initializes the BigSdbApi instance with an optional hostname, API key, and SSL verification flag.
        
        get_resources(self) -> models.ResourceList:
            Retrieves the list of resources available from the BigSdb API.
        
        get_databases(self, pattern: str = None, category: str = None, 
                      exact_match: bool = False, use_regex: bool = False) -> models.DatabaseList:
            Retrieves and optionally filters the list of databases from the BigSdb API.
    """

    hostname: str = ''

    def __init__(self, hostname: str = None, api_key: str = '', ssl_verify: bool = True) -> None:
        super().__init__(api_key, ssl_verify)
        self.hostname = hostname if hostname else self.hostname

    def get_resources(self) -> models.ResourceList:
        """
        Retrieves the list of resources available from the BigSdb API.

        Returns:
            models.ResourceList: A list of resources available from the BigSdb API.
        """

        resources = ResourceApi.from_url(self.hostname)
        return resources.model.resources
    
    def get_databases(self, pattern: str = None, category: str = None, 
                      exact_match: bool = False, use_regex: bool = False) -> models.DatabaseList:
        # Get the databases in the API, NOT THE SCHEMES
        """
        Retrieves and optionally filters the list of databases from the BigSdb API.

        Args:
            pattern (str, optional): A pattern to match against database subjects. Default is None.
            category (str, optional): A category to filter databases. Default is None.
            exact_match (bool, optional): Whether to require an exact match for the pattern. Default is False.
            use_regex (bool, optional): Whether to interpret the pattern as a regular expression. Default is False.

        Returns:
            models.DatabaseList: A list of databases from the BigSdb API, filtered according to the provided criteria.
        """
        resources = self.get_resources()
        dbs = [resource.databases for resource in resources]
        databases = models.DatabaseList.from_list_of_model_lists(dbs)

        if pattern or category:
            databases = databases.search('subject', pattern, category, exact_match, use_regex)

        return databases
        
    
class PubMlstApi(BigSdbApi):
    hostname = 'https://rest.pubmlst.org/'

class PasteurApi(BigSdbApi):
    hostname = 'https://bigsdb.pasteur.fr/api'

class ApiModelService(ApiService):

    """
    A service class that interacts with API models, providing methods to instantiate and work with them.

    Attributes:
        _base_model (Type): The base model class that will be used to instantiate the model from API data.
        model: An instance of the model class that is initialized with API data.

    Methods:
        __init__(self, model, api_key: str = '', ssl_verify: bool = True) -> None:
            Initializes the ApiModelService instance with a specific model, API key, and SSL verification flag.
        
        from_url(cls, url: str, api_key: str = '', ssl_verify: bool = True) -> 'ApiModelService':
            Class method to create an instance of ApiModelService from a URL that returns model data.
    """
    _base_model = None

    def __init__(self, model, api_key: str = '', ssl_verify: bool = True) -> None:
        super().__init__(api_key, ssl_verify)
        self.model = model

    @classmethod
    def from_url(cls, url, api_key: str = '', ssl_verify: bool = True) -> 'ApiModelService':
        """
        Creates an instance of ApiModelService from a URL that provides data to initialize the model.

        Args:
            url (str): The URL from which to fetch the model data.
            api_key (str, optional): The API key for authentication. Default is an empty string.
            ssl_verify (bool, optional): Flag indicating whether SSL verification should be performed. Default is True.

        Returns:
            ApiModelService: An instance of ApiModelService initialized with the model data fetched from the URL.
        """
        rest = RestClient(api_key, ssl_verify)
        metadata = rest.get(url)
        print(metadata.json())
        model = cls._base_model.from_json(metadata.json())
        return cls(model, api_key, ssl_verify)

class ResourceApi(ApiModelService):
    """
    A service class specifically designed to interact with API resources

    Attributes:
        _base_model (Type): The base model class used to instantiate the resource model from API data. 
                            In this case, it is set to models.ApiResourceCollectionModel.

    Methods:
        from_url(cls, url: str, api_key: str = '', ssl_verify: bool = True) -> ApiModelService:
            Class method to create an instance of ResourceApi from a URL that returns resource data.
    """

    _base_model = models.ApiResourceCollectionModel


class FullDatabaseApi(ApiModelService):
    """
    A service class for interacting with full database resources in an API, extending the ApiModelService.

    Attributes:
        _base_model (Type): The base model class used to instantiate the database model from API data.
                            In this case, it is set to models.FullDatabaseModel.

    Methods:
        get_schemes(self, pattern: str = None, category: str = None, exact_match: bool = True) -> models.SchemeList:
            Retrieves and optionally filters a list of schemes from the database based on the provided criteria.
    """
    
    _base_model = models.FullDatabaseModel

    def get_schemes(self, pattern: str = None, category: str = None, exact_match: bool = True) -> models.SchemeList:
        """
        Retrieves a list of schemes from the database and filters them based on a pattern and category if provided.

        Args:
            pattern (str, optional): A pattern to match against scheme names. Default is None.
            category (str, optional): A category to filter schemes. Default is None.
            exact_match (bool, optional): Whether to require an exact match for the pattern. Default is True.

        Returns:
            models.SchemeList: A list of schemes filtered according to the provided criteria.
        """
        
        response = self.rest_client.get(self.model.schemes)
        scheme_list= models.SchemeCollectionModel(**response.json()).schemes

        if pattern or category:
            scheme_list = scheme_list.search('scheme', pattern, category, exact_match)

        return scheme_list


class SchemeCollectionApi(ApiModelService):
    _base_model = models.SchemeCollectionModel

    def return_scheme_by_idx(self, idx):
        index_dict = {scheme.scheme.split('/')[-1] : scheme for scheme in self.model}
        idx = str(idx)
        if idx in index_dict:
            return index_dict[idx]
        else:
            raise ValueError(f'Provided idx {idx} not in schemes')


class SequenceQueryHandler(ApiService):

    query_endpoint: str = None

    def __init__(self, query_endpoint: str = None, api_key: str = '', ssl_verify: bool = True) -> None:
        super().__init__(api_key, ssl_verify)
        
        if query_endpoint:
            self.query_endpoint = query_endpoint

    def query_sequence(self, sequence, details: bool = False, partial_matches: bool = True, **kwargs ) -> Dict:
        # Hay que generalizar este método
        base_64 = utils.is_base64(sequence)
        payload = {
            'sequence' : sequence,
            'details' : details,
            'partial_matches': partial_matches,
            'base64' : base_64
        }
        response = self.rest_client.post(self.query_endpoint, json=payload, **kwargs)
        return response.json()

class SchemeApi(ApiModelService):
    _base_model = models.SchemeModel

    def get_full_scheme(self) -> models.FullSchemeModel:
        response = self.rest_client.get(self.model.scheme)
        full_scheme = models.FullSchemeModel(**response.json())
        return full_scheme

    def query_sequence(self, sequence, details: bool = True, partial_matches: bool = True, **kwargs ):

        sequence_handler = SequenceQueryHandler(self.model.query_endpoint)
        response = sequence_handler.query_sequence(sequence, details, partial_matches, **kwargs)
        result = models.SchemeQueryResult(**response)
        return result
        

class FullSchemeApi(ApiModelService):
    _base_model = models.FullSchemeModel

    def __init__(self, model: models.FullSchemeModel, api_key: str = '', ssl_verify: bool = True) -> None:
        super().__init__(model, api_key=api_key, ssl_verify=ssl_verify)
        self._indexed_locis = self._index_loci()

    def get_profiles(self) -> pd.DataFrame:
        # Read the profiles csv and return df
        response = self.rest_client.get(self.model.profiles_csv)
        data = StringIO(response.text)
        df = pd.read_table(data)
        return df

    def list_loci(self) -> List[str]:

        return [loci for loci in self._indexed_locis.keys()]
    
    def _index_loci(self) -> Dict[str, str]:

        locis = {loci.split('/')[-1] : loci for loci in self.model.loci}
        return locis

    def get_alleles_fasta(self, loci: str):

        if loci in self._indexed_locis:
            loci_serv = LociApi.from_url(self._indexed_locis[loci])
            return loci_serv.get_alleles()
        else:
            print('Loci does not exits') # COnvertir en raise error
            return None

    def get_scheme_fastas(self):
        # Get all the alleles!
        return {loci: self.get_alleles_fasta(loci) for loci in self._indexed_locis.keys()}


    
class LociApi(ApiModelService):
    _base_model = models.LociModel

    def get_alleles(self) -> SeqIO.FastaIO.FastaIterator:
        response = self.rest_client.get(self.model.alleles_fasta)
        fasta = SeqIO.parse(StringIO(response.text), 'fasta')
        return fasta

    @classmethod
    def from_url(cls, url ,api_key: str = '', ssl_verify: bool = True) -> 'LociApi':
        rest_client = RestClient(api_key=api_key, ssl_verify=ssl_verify)
        data = rest_client.get(url)
        loci = models.LociModel(**data.json())

        return cls(loci, api_key, ssl_verify)


class rMLST(SequenceQueryHandler):
    query_endpoint = 'http://rest.pubmlst.org/db/pubmlst_rmlst_seqdef_kiosk/schemes/1/sequence'

    def query_sequence(self, sequence, details: bool = True, partial_matches: bool = False, **kwargs):
        response =  super().query_sequence(sequence, details, partial_matches, **kwargs)
        result = models.rMLSTResultModel(**response)
        return result
    
