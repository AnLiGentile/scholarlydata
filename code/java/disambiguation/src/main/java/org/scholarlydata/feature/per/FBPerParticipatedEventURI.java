package org.scholarlydata.feature.per;

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
 *
 */
public class FBPerParticipatedEventURI extends FeatureBuilderSPARQL<FeatureType, List<String>> {
    public FBPerParticipatedEventURI(String sparqlEndpoint,
                                     SolrCache cache) {
        super(sparqlEndpoint, cache);
    }

    @Override
    public Pair<FeatureType, List<String>> build(String objId) {
        String queryStr = SPARQLQueries.pathObjObj(objId,
                Predicate.PERSON_hasAffliation.getURI(),
                Predicate.FUNCTION_during.getURI());

        Object cached = getFromCache(queryStr);
        if (cached != null)
            return new ImmutablePair<>(FeatureType.PERSON_PARTICIPATED_EVENT_URI,
                    (List<String>) cached);

        ResultSet rs = query(queryStr);
        List<String> result = getListResult(rs);
        saveToCache(queryStr, result);
        return new ImmutablePair<>(FeatureType.PERSON_PARTICIPATED_EVENT_URI, result);
    }
}
