from typing import List, Dict, Optional
import os

from httpx import Client

class IPFClient (Client):
    def __init__ (self, *vargs, snapshot_id = '$last', **kwargs):
        try:
            assert kwargs.setdefault('base_url',os.environ['IPF_ADDR'])
        except (AssertionError, KeyError):
            raise RuntimeError(
                f'base_url not provided or IPF_ADDR not set'
            )
        kwargs['base_url']+='/api/v1'
        token = os.environ['IPF_TOKEN']
        super().__init__(*vargs, verify=False, **kwargs)
        self.headers['X-API-Token'] = token
        self.snapshot_id = snapshot_id

    def fetch_table(self, url, columns: List[str], filters: Optional[Dict] = None, pagination: Optional[Dict] = None, snapshot_id: Optional[str] = None):
        payload = dict(columns=columns,snapshot=snapshot_id or self.snapshot_id)
        if filters:
            payload['filters']=filters

        if pagination:
            payload['pagination']=pagination

        res=self.post(url,json=payload)
        res.raise_for_status()
        body=res.json()
        return body['data'] 
        
