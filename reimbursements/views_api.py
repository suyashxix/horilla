from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from .models import Reimbursement
from .serializers import ReimbursementSerializer


class ReimbursementUploadAPI(APIView):
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request):
        serializer = ReimbursementSerializer(data=request.data)
        if serializer.is_valid():
            reimbursement = serializer.save()
            amount, vendor = None, None
            reimbursement.amount = amount
            reimbursement.vendor = vendor
            reimbursement.save()
            return Response(ReimbursementSerializer(reimbursement).data, status=201)
        return Response(serializer.errors, status=400)
    

class ReimbursementListAPI(APIView):
    def get(self, request):
        reimbursements = Reimbursement.objects.all()
        serializer = ReimbursementSerializer(reimbursements, many=True)
        return Response(serializer.data)
    

class ReimbursementDetailAPI(APIView):
    def get(self, request, pk):
        try:
            reimbursement = Reimbursement.objects.get(pk=pk)
            serializer = ReimbursementSerializer(reimbursement)
            return Response(serializer.data)
        except Reimbursement.DoesNotExist:
            return Response({'error': 'Not found'}, status=404)
        

class MarkReimbursementDoneAPI(APIView):
    def put(self, request, pk):
        try:
            reimbursement = Reimbursement.objects.get(pk=pk)
            reimbursement.status = 'done'
            reimbursement.save()
            return Response({'message': 'Marked as done'})
        except Reimbursement.DoesNotExist:
            return Response({'error': 'Not found'}, status=404)

