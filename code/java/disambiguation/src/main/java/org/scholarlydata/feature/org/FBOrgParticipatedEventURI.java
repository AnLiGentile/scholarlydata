package org.scholarlydata.feature.org;

import org.apache.commons.lang3.tuple.ImmutablePair;
import org.apache.commons.lang3.tuple.Pair;
import org.apache.jena.query.ResultSet;
import org.scholarlydata.SPARQLQueries;
import org.scholarlydata.feature.FeatureBuilderSPARQL;
import org.scholarlydata.feature.FeatureType;
import org.scholarlydata.feature.Predicate;
import org.scholarlydata.util.SolrCache;

import java.util.List;

/**
 * Created by zqz on 18/11/16.
 */
public class FBOrgParticipatedEventURI extends FeatureBuilderSPARQL<FeatureType, List<String>> {


    public FBOrgParticipatedEventURI(String sparqlEndpoint,
                                     SolrCache cache) {
        super(sparqlEndpoint, cache);
    }

    @Override
    public Pair<FeatureType, List<String>> build(String objId) {
        String queryStr = SPARQLQueries.pathSubObj(objId,
                Predicate.AFFLIATION_withOrganization.getURI(),
                Predicate.FUNCTION_during.getURI());

        Object cached=getFromCache(queryStr);
        if(cached!=null)
            return new ImmutablePair<>(FeatureType.ORGANISATION_PARTICIPATED_EVENT_URI,(List<String>) cached);

        ResultSet rs = query(queryStr);
        List<String> result = getListResult(rs);
        saveToCache(queryStr, result);
        return new ImmutablePair<>(FeatureType.ORGANISATION_PARTICIPATED_EVENT_URI, result);
    }
}
