from rest_framework import status, generics
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import IsAuthenticated, SAFE_METHODS
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsCharityOwner, IsBenefactor
from charities.models import Task
from charities.serializers import (
    TaskSerializer, CharitySerializer, BenefactorSerializer
)


class BenefactorRegistration(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        serializer_benefactor = BenefactorSerializer(data=request.data)
        if serializer_benefactor.is_valid():
            serializer_benefactor.save(user=request.user)
            return Response({'message':serializer_benefactor.data})
        return Response({'message': serializer_benefactor.errors})


class CharityRegistration(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        serializer_charity = CharitySerializer(data=request.data)
        if serializer_charity.is_valid():
            serializer_charity.save(user=request.user)
            return Response({'message':serializer_charity.data})
        return Response({'message': serializer_charity.errors})


class Tasks(generics.ListCreateAPIView):
    serializer_class = TaskSerializer

    def get_queryset(self):
        return Task.objects.all_related_tasks_to_user(self.request.user)

    def post(self, request, *args, **kwargs):
        data = {
            **request.data,
            "charity_id": request.user.charity.id
        }
        serializer = self.serializer_class(data = data)
        serializer.is_valid(raise_exception = True)
        serializer.save()
        return Response(serializer.data, status = status.HTTP_201_CREATED)

    def get_permissions(self):
        if self.request.method in SAFE_METHODS:
            self.permission_classes = [IsAuthenticated, ]
        else:
            self.permission_classes = [IsCharityOwner, ]

        return [permission() for permission in self.permission_classes]

    def filter_queryset(self, queryset):
        filter_lookups = {}
        for name, value in Task.filtering_lookups:
            param = self.request.GET.get(value)
            if param:
                filter_lookups[name] = param
        exclude_lookups = {}
        for name, value in Task.excluding_lookups:
            param = self.request.GET.get(value)
            if param:
                exclude_lookups[name] = param

        return queryset.filter(**filter_lookups).exclude(**exclude_lookups)


class TaskRequest(APIView):
    permission_classes = [IsBenefactor,IsAuthenticated]
    def get(self, request,task_id):
        task = get_object_or_404(Task,id=task_id)
        if task.state!='P':
            data={'detail': 'This task is not pending.'}
            return Response(data,status=404)
        else:
            task.state = "W"
            task.assigned_benefactor = request.user.benefactor
            task.save()
            data={'detail': 'Request sent.'}
            return Response(data,status=200)



class TaskResponse(APIView):
    permission_classes = [IsCharityOwner,IsAuthenticated]
    def post(self,request,task_id):
        task = Task.objects.get(id=task_id)
        response=request.data['response']
        if response!='A'and response!='R':
            data={'detail': 'Required field ("A" for accepted / "R" for rejected)'}
            return Response(data,status=400)
        if task.state !='W':
            data={'detail': 'This task is not waiting.'}
            return Response(data,status=404)
        else:
            if response=='A':
                task.state='A'
                task.save()
                data={'detail': 'Response sent.'}
                return Response(data,status=200)
            if response=='R':
                task.state='P'
                task.assigned_benefactor = None
                task.save()
                data={'detail': 'Response sent.'}
                return Response(data,status=200)


class DoneTask(APIView):
    permission_classes = [IsCharityOwner,IsAuthenticated]
    def post(self,request,task_id):
        task = get_object_or_404(Task,id=task_id)
        if task.state != 'A':
            data={'detail': 'Task is not assigned yet.'}
            return Response(data,status=404)
        else:
            task.state='D'
            task.save()
            data={'detail': 'Task has been done successfully.'}
            return Response(data,status=200)
